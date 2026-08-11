#!/usr/bin/env python3
"""Daily update: append new AMZN sessions to history.csv, regenerate
index.html, and alert if the history has gone stale.

Never rewrites existing rows in history.csv — see amzn_stock_SPEC.md.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from lib.fx import fetch_ecb_rates
from lib.history import HistoryRow, append_rows, count_data_rows, read_all_rows, read_last_date, verify_integrity
from lib.prices import fetch_new_prices
from lib.render import render_index_html

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_HISTORY = REPO_ROOT / "amzn_stock_history.csv"
DEFAULT_TEMPLATE = REPO_ROOT / "amzn_stock_template.html"
DEFAULT_OUTPUT = REPO_ROOT / "index.html"

STALE_AFTER_BUSINESS_DAYS = 5

# How far to pad the ECB rate window before `last_date`: covers both new
# sessions and the tail lookback render.build_sources_note needs to
# describe any forward-fill currently in effect.
FX_WINDOW_BUFFER_DAYS = 30


def business_days_since(last_date: date, today: date) -> int:
    days = 0
    d = last_date
    while d < today:
        d += timedelta(days=1)
        if d.weekday() < 5:  # Monday=0 .. Sunday=6
            days += 1
    return days


def run_update(history_path: Path, template_path: Path, output_path: Path, today: date | None = None) -> bool:
    """Run the full pipeline. Returns True if the history is fresh enough."""
    today = today or date.today()

    last_date = read_last_date(history_path)
    previous_row_count = count_data_rows(history_path)

    new_prices, price_source = fetch_new_prices(last_date)
    print(f"{len(new_prices)} new session(s) from {price_source}")

    fx_window_start = last_date - timedelta(days=FX_WINDOW_BUFFER_DAYS)
    fx = fetch_ecb_rates(fx_window_start, today)

    if new_prices:
        new_rows = []
        for price in new_prices:
            eur_per_usd, rate_date = fx.eur_per_usd_asof(price.trade_date)
            close_eur = round(price.close_usd * eur_per_usd, 6)
            new_rows.append(
                HistoryRow(
                    trade_date=price.trade_date,
                    close_usd=price.close_usd,
                    eur_per_usd=eur_per_usd,
                    close_eur=close_eur,
                    fx_source="ecb",
                )
            )
            if rate_date != price.trade_date:
                print(f"  {price.trade_date}: no ECB quote, carrying forward rate from {rate_date}")
        append_rows(history_path, new_rows)

    verify_integrity(history_path, previous_row_count)

    all_rows = read_all_rows(history_path)
    render_index_html(template_path, output_path, all_rows, fx)

    last_date = read_last_date(history_path)
    gap = business_days_since(last_date, today)
    fresh = gap <= STALE_AFTER_BUSINESS_DAYS
    if not fresh:
        print(
            f"STALE: history.csv's last session is {last_date}, "
            f"{gap} business day(s) behind {today} (limit: {STALE_AFTER_BUSINESS_DAYS}). "
            "A price source may be down — check manually.",
            file=sys.stderr,
        )
    return fresh


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, default=DEFAULT_HISTORY)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    fresh = run_update(args.history, args.template, args.output)
    return 0 if fresh else 1


if __name__ == "__main__":
    sys.exit(main())
