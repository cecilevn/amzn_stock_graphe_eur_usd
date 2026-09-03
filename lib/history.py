"""Read and append-only-update history.csv.

Non-negotiable rule (see amzn_stock_SPEC.md): this module never rewrites
or recomputes an existing row. It only reads the current file and
appends new rows at the end, in chronological order.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

CSV_COLUMNS = ["date", "close_usd", "eur_per_usd", "close_eur", "fx_source"]
FIRST_SESSION = date(1997, 5, 15)


@dataclass(frozen=True)
class HistoryRow:
    trade_date: date
    close_usd: float
    eur_per_usd: float
    close_eur: float
    fx_source: str

    def to_csv_fields(self) -> list[str]:
        return [
            self.trade_date.isoformat(),
            f"{self.close_usd:.6f}",
            f"{self.eur_per_usd:.6f}",
            f"{self.close_eur:.6f}",
            self.fx_source,
        ]


def read_all_rows(csv_path: Path) -> list[HistoryRow]:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            HistoryRow(
                trade_date=date.fromisoformat(record["date"]),
                close_usd=float(record["close_usd"]),
                eur_per_usd=float(record["eur_per_usd"]),
                close_eur=float(record["close_eur"]),
                fx_source=record["fx_source"],
            )
            for record in reader
        ]


def read_last_date(csv_path: Path) -> date:
    """Return the date on the last data line, without loading the whole file into memory."""
    last_date_field = None
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if row:
                last_date_field = row[0]
    if last_date_field is None:
        raise ValueError(f"{csv_path} has no data rows")
    return date.fromisoformat(last_date_field)


def count_data_rows(csv_path: Path) -> int:
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1  # minus header


def append_rows(csv_path: Path, rows: list[HistoryRow]) -> None:
    """Append new rows in chronological order. Never touches existing lines."""
    if not rows:
        return
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        for row in sorted(rows, key=lambda r: r.trade_date):
            writer.writerow(row.to_csv_fields())


def verify_integrity(csv_path: Path, previous_row_count: int) -> None:
    """Enforce the two invariants the spec requires after every run.

    First data row must still be 1997-05-15, and the row count must
    never have decreased.
    """
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        if header != CSV_COLUMNS:
            raise ValueError(f"{csv_path}: unexpected header {header}")
        first_row = next(reader)
        row_count = 1
        for _ in reader:
            row_count += 1

    first_date = date.fromisoformat(first_row[0])
    if first_date != FIRST_SESSION:
        raise ValueError(f"{csv_path}: first row is {first_date}, expected {FIRST_SESSION}")
    if row_count < previous_row_count:
        raise ValueError(
            f"{csv_path}: row count dropped from {previous_row_count} to {row_count}"
        )
