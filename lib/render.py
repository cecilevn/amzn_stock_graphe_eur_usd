"""Build index.html from the template: inject the data JSON and refresh
the two spots the spec calls out as hardcoded (period line, forward-fill
footnote)."""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from .fx import FxRates
from .history import HistoryRow

_MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# How far back to look for an active forward-fill streak at the tail of
# the series. A handful of sessions covers any realistic holiday gap.
_TAIL_LOOKBACK = 20


def round_sig(value: float, sig: int) -> float:
    if value == 0:
        return 0.0
    digits = sig - 1 - math.floor(math.log10(abs(value)))
    return round(value, digits)


def format_date_fr(d: date) -> str:
    return f"{d.day} {_MONTHS_FR[d.month - 1]} {d.year}"


def format_count_fr(n: int) -> str:
    return format(n, ",").replace(",", " ")


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


def build_period_text(rows: list[HistoryRow]) -> str:
    first, last = rows[0].trade_date, rows[-1].trade_date
    return f"{format_date_fr(first)} → {format_date_fr(last)} · {format_count_fr(len(rows))} séances"


def build_sources_note(rows: list[HistoryRow], fx: FxRates) -> str:
    base_sentence = (
        "Sources : cours quotidiens Stooq (repli yfinance en cas de panne) ; "
        "taux écu/dollar de la Fed de New York (H.10) avant 1999, taux de référence "
        "quotidien euro/dollar de la Banque centrale européenne depuis. Le taux de change "
        "n'étant publié que les jours ouvrés européens, le dernier taux connu est "
        "reporté sur les séances sans cotation de change"
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
        clause = f" ; le cours du {format_date_fr(block_dates[0])} utilise le taux du {format_date_fr(rate_date)}, dernier disponible dans la série."
    else:
        clause = (
            f" ; les cours du {format_date_fr(block_dates[0])} au {format_date_fr(block_dates[-1])} "
            f"utilisent le taux du {format_date_fr(rate_date)}, dernier disponible dans la série."
        )
    return base_sentence + clause


def render_index_html(template_path: Path, output_path: Path, rows: list[HistoryRow], fx: FxRates) -> None:
    template = template_path.read_text(encoding="utf-8")
    html = (
        template
        .replace("__DATA__", build_data_json(rows))
        .replace("__PERIOD__", build_period_text(rows))
        .replace("__SOURCES_NOTE__", build_sources_note(rows, fx))
    )
    output_path.write_text(html, encoding="utf-8")
