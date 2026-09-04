"""Fetch AMZN daily closes newer than a given date.

Primary source: Stooq CSV export. Fallbacks, tried in order, only used
when the previous source fails outright: yfinance (undocumented Yahoo
API, breaks a couple of times a year), then Nasdaq's own historical
quote endpoint (also undocumented, same risk class as yfinance — kept
as a second, independent fallback so one source's outage doesn't stop
updates while another is down at the same time — see
amzn_stock_SPEC.md).
"""

from __future__ import annotations

import csv
import io
import math
from datetime import date
from typing import NamedTuple

import requests

STOOQ_URL = "https://stooq.com/q/d/l/?s=amzn.us&i=d"
NASDAQ_URL = "https://api.nasdaq.com/api/quote/AMZN/historical"
USER_AGENT = "Mozilla/5.0 (compatible; amzn-eur-updater/1.0; +https://github.com/cecilevn/amzn_stock_graphe_eur_usd)"
# api.nasdaq.com hangs (soft-blocks, no response until read timeout) on
# the honest UA above — it only replies to something that looks like a
# real browser. Confirmed 2026-09-04.
NASDAQ_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
REQUEST_TIMEOUT = 30


class PriceRow(NamedTuple):
    trade_date: date
    close_usd: float


class SourceError(RuntimeError):
    """A price source failed or returned something unusable."""


def _reject_non_finite(rows: list[PriceRow], source: str) -> list[PriceRow]:
    """A source occasionally reports an unsettled session as NaN (seen from
    yfinance when the latest close hasn't finalized yet). Treat that as a
    fetch failure rather than writing it to history.csv — the caller falls
    back to the other source, or surfaces the failure."""
    for row in rows:
        if not math.isfinite(row.close_usd):
            raise SourceError(f"{source}: non-finite close {row.close_usd!r} for {row.trade_date}")
    return rows


def fetch_stooq(since: date) -> list[PriceRow]:
    resp = requests.get(STOOQ_URL, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    text = resp.text.strip()
    if not text or text.startswith("<"):
        raise SourceError(f"stooq: unexpected response body: {text[:120]!r}")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or "Date" not in reader.fieldnames or "Close" not in reader.fieldnames:
        raise SourceError(f"stooq: unexpected columns: {reader.fieldnames}")

    rows = []
    for record in reader:
        trade_date = date.fromisoformat(record["Date"])
        if trade_date > since:
            rows.append(PriceRow(trade_date, float(record["Close"])))
    rows.sort(key=lambda r: r.trade_date)
    return _reject_non_finite(rows, "stooq")


def fetch_yfinance(since: date) -> list[PriceRow]:
    """Raises on a genuine fetch failure. An empty result is not an error —
    it just means no session newer than `since` is available yet, same as
    an empty-but-well-formed Stooq response."""
    import yfinance as yf  # lazy import: only needed on fallback

    hist = yf.Ticker("AMZN").history(start=since.isoformat(), auto_adjust=True)

    rows = []
    for ts, record in hist.iterrows():
        trade_date = ts.date()
        if trade_date > since:
            rows.append(PriceRow(trade_date, round(float(record["Close"]), 6)))
    rows.sort(key=lambda r: r.trade_date)
    return _reject_non_finite(rows, "yfinance")


def fetch_nasdaq(since: date) -> list[PriceRow]:
    resp = requests.get(
        NASDAQ_URL,
        params={
            "assetclass": "stocks",
            "fromdate": since.isoformat(),
            "todate": date.today().isoformat(),
            "limit": "200",
        },
        headers={"User-Agent": NASDAQ_USER_AGENT, "Accept": "application/json"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    try:
        payload = resp.json()
        table_rows = payload["data"]["tradesTable"]["rows"] or []
    except (ValueError, KeyError, TypeError) as exc:
        raise SourceError(f"nasdaq: unexpected response body: {resp.text[:120]!r}") from exc

    rows = []
    for record in table_rows:
        month, day, year = (int(p) for p in record["date"].split("/"))
        trade_date = date(year, month, day)
        if trade_date > since:
            close = float(record["close"].lstrip("$").replace(",", ""))
            rows.append(PriceRow(trade_date, close))
    rows.sort(key=lambda r: r.trade_date)
    return _reject_non_finite(rows, "nasdaq")


def fetch_new_prices(since: date) -> tuple[list[PriceRow], str]:
    """Return (new rows strictly after `since`, source name used).

    Tries Stooq first, then yfinance, then Nasdaq. Only advances to the
    next source if the current one raises — an empty-but-well-formed
    response (no new session yet) is not an error and does not trigger
    the fallback.
    """
    errors = {}
    for source_name, fetch in (("stooq", fetch_stooq), ("yfinance", fetch_yfinance), ("nasdaq", fetch_nasdaq)):
        try:
            return fetch(since), source_name
        except Exception as error:
            errors[source_name] = error

    raise SourceError(
        "all price sources failed: " + ", ".join(f"{name}={error!r}" for name, error in errors.items())
    ) from errors["nasdaq"]
