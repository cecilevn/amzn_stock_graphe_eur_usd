from datetime import date

from lib.fx import FxRates
from lib.history import HistoryRow
from lib.render import build_sources_note, format_date, round_sig


def make_tail_rows():
    return [
        HistoryRow(date(2026, 7, 29), 226.649994, 0.8783, 199.06669, "fed_h10_eur"),
        HistoryRow(date(2026, 7, 30), 235.5, 0.8783, 206.83965, "fed_h10_eur"),
        HistoryRow(date(2026, 7, 31), 271.579987, 0.8783, 238.528702, "fed_h10_eur"),
    ]


def test_round_sig():
    assert round_sig(271.579987, 6) == 271.58
    assert round_sig(0.097917123, 6) == 0.0979171


def test_format_date():
    assert format_date(date(1997, 5, 15)) == "15 May 1997"


def test_sources_note_no_active_forward_fill():
    rows = make_tail_rows()
    fx = FxRates({date(2026, 7, 31): 1.138})  # own-day quote for the last row
    note = build_sources_note(rows, fx)
    assert "uses the" not in note
    assert "use the" not in note
    assert note.endswith(".")


def test_sources_note_reports_active_forward_fill_block():
    rows = make_tail_rows()
    fx = FxRates({date(2026, 7, 24): 1.138})  # only a quote from a week earlier
    note = build_sources_note(rows, fx)
    assert "24 July 2026" in note
    assert "use the" in note
    assert "29 July 2026" in note and "31 July 2026" in note
