"""The non-negotiable rule from amzn_stock_SPEC.md: history.csv is only
ever appended to. These tests run against a copy of the real file to
catch any regression that would rewrite or shrink it."""

import shutil
from datetime import date
from pathlib import Path

import pytest

from lib import history

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_HISTORY = REPO_ROOT / "amzn_stock_history.csv"


@pytest.fixture
def history_copy(tmp_path):
    dst = tmp_path / "history.csv"
    shutil.copy(REAL_HISTORY, dst)
    return dst


def test_first_row_is_ipo_date(history_copy):
    rows = history.read_all_rows(history_copy)
    assert rows[0].trade_date == history.FIRST_SESSION == date(1997, 5, 15)


def test_verify_integrity_passes_on_untouched_file(history_copy):
    count = history.count_data_rows(history_copy)
    history.verify_integrity(history_copy, count)  # must not raise


def test_verify_integrity_rejects_moved_first_row(history_copy):
    count = history.count_data_rows(history_copy)
    lines = history_copy.read_text(encoding="utf-8").splitlines(keepends=True)
    corrupted = [lines[0]] + lines[2:]  # header + everything but the first data row
    history_copy.write_text("".join(corrupted), encoding="utf-8")
    with pytest.raises(ValueError, match="first row"):
        history.verify_integrity(history_copy, count)


def test_verify_integrity_rejects_shrinking_row_count(history_copy):
    count = history.count_data_rows(history_copy)
    lines = history_copy.read_text(encoding="utf-8").splitlines(keepends=True)
    history_copy.write_text("".join(lines[:-10]), encoding="utf-8")
    with pytest.raises(ValueError, match="row count dropped"):
        history.verify_integrity(history_copy, count)


def test_append_rows_never_touches_existing_bytes(history_copy):
    original = history_copy.read_bytes()
    original_count = history.count_data_rows(history_copy)

    new_rows = [
        history.HistoryRow(date(2026, 8, 3), 280.0, 0.87, 243.6, "ecb"),
        history.HistoryRow(date(2026, 8, 4), 281.5, 0.871, 245.19, "ecb"),
    ]
    history.append_rows(history_copy, new_rows)

    updated = history_copy.read_bytes()
    assert updated.startswith(original)
    assert history.count_data_rows(history_copy) == original_count + 2
    history.verify_integrity(history_copy, original_count)


def test_append_rows_sorts_new_rows_chronologically(history_copy):
    history.append_rows(
        history_copy,
        [
            history.HistoryRow(date(2026, 8, 4), 281.5, 0.871, 245.19, "ecb"),
            history.HistoryRow(date(2026, 8, 3), 280.0, 0.87, 243.6, "ecb"),
        ],
    )
    tail = history.read_all_rows(history_copy)[-2:]
    assert [row.trade_date for row in tail] == [date(2026, 8, 3), date(2026, 8, 4)]


def test_read_last_date(history_copy):
    assert history.read_last_date(history_copy) == date(2026, 7, 31)
