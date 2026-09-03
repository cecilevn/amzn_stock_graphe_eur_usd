"""Fetch AMZN daily closes newer than a given date.

Primary source: Stooq CSV export. Fallback: yfinance, only used when
Stooq fails outright — never routinely, since yfinance wraps an
undocumented Yahoo API that breaks a couple of times a year.
"""

from __future__ import annotations

import csv
import io
import math
from datetime import date
from typing import NamedTuple

import requests

STOOQ_URL = "https://stooq.com/q/d/l/?s=amzn.us&i=d"
USER_AGENT = "Mozilla/5.0 (compatible; amzn-eur-updater/1.0; +https://github.com/cecilevn/amzn_stock_graphe_eur_usd)"
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


def fetch_new_prices(since: date) -> tuple[list[PriceRow], str]:
    """Return (new rows strictly after `since`, source name used).

    Tries Stooq first. Only falls back to yfinance if Stooq raises —
    an empty-but-well-formed Stooq response (no new session yet) is not
    an error and does not trigger the fallback.
    """
    try:
        return fetch_stooq(since), "stooq"
    except Exception as stooq_error:
        try:
            return fetch_yfinance(since), "yfinance"
        except Exception as yfinance_error:
            raise SourceError(
                f"both price sources failed: stooq={stooq_error!r}, yfinance={yfinance_error!r}"
            ) from yfinance_error
