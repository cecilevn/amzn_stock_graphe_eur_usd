"""Build index.html from the template: inject the data JSON and refresh
the sources footnote the spec calls out as hardcoded (which date's rate
is currently being carried forward, if any)."""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from .fx import FxRates
from .history import HistoryRow

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# How far back to look for an active forward-fill streak at the tail of
# the series. A handful of sessions covers any realistic holiday gap.
_TAIL_LOOKBACK = 20


def round_sig(value: float, sig: int) -> float:
    if value == 0:
        return 0.0
    digits = sig - 1 - math.floor(math.log10(abs(value)))
    return round(value, digits)


def format_date(d: date) -> str:
    return f"{d.day} {_MONTHS[d.month - 1]} {d.year}"


def build_data_json(rows: list[HistoryRow]) -> str:
    base = rows[0].trade_date
    payload = {
        "base": base.isoformat(),
        "t": [(row.trade_date - base).days for row in rows],
        "usd": [round_sig(row.close_usd, 6) for row in rows],
        "eur": [round_sig(row.close_eur, 6) for row in rows],
        "fx": [round_sig(1.0 / row.eur_per_usd, 5) for row in rows],
    }
    return json.dumps(payload, separators=(",", ":"))


def build_sources_note(rows: list[HistoryRow], fx: FxRates) -> str:
    base_sentence = (
        "Sources: daily prices from Stooq (falls back to Yahoo Finance via "
        "yfinance on failure); FX rate from the Fed's New York ECU/dollar "
        "series (H.10) before 1999, the European Central Bank's daily "
        "euro/dollar reference rate since. The FX rate is only published on "
        "European business days, so the latest known rate is carried "
        "forward on sessions without one"
    )

    resolved = []
    for row in rows[-_TAIL_LOOKBACK:]:
        try:
            resolved.append((row.trade_date, fx.eur_per_usd_asof(row.trade_date)[1]))
        except ValueError:
            # No ECB coverage this far back (e.g. near the 1999 boundary):
            # nothing to report for this row, restart the tail from here.
            resolved = []

    if not resolved or resolved[-1][0] == resolved[-1][1]:
        # Most recent session used its own day's rate: no active forward-fill.
        return base_sentence + "."

    rate_date = resolved[-1][1]
    block_dates = []
    for session, asof in reversed(resolved):
        if asof != rate_date:
            break
        block_dates.append(session)
    block_dates.reverse()

    if len(block_dates) == 1:
        clause = f"; the {format_date(block_dates[0])} price uses the {format_date(rate_date)} rate, the latest available in the series."
    else:
        clause = (
            f"; prices from {format_date(block_dates[0])} to {format_date(block_dates[-1])} "
            f"use the {format_date(rate_date)} rate, the latest available in the series."
        )
    return base_sentence + " " + clause


def render_index_html(template_path: Path, output_path: Path, rows: list[HistoryRow], fx: FxRates) -> None:
    template = template_path.read_text(encoding="utf-8")
    html = (
        template
        .replace("__DATA__", build_data_json(rows))
        .replace("__SOURCES_NOTE__", build_sources_note(rows, fx))
    )
    output_path.write_text(html, encoding="utf-8")
