from datetime import date

from lib.fx import FxRates
from lib.history import HistoryRow
from lib.render import build_period_text, build_sources_note, format_date_fr, round_sig


def make_long_span_rows():
    return [
        HistoryRow(date(1997, 5, 15), 0.097917, 0.87108, 0.085294, "fed_h10_ecu"),
        HistoryRow(date(2026, 7, 30), 235.5, 0.8783, 206.83965, "fed_h10_eur"),
        HistoryRow(date(2026, 7, 31), 271.579987, 0.8783, 238.528702, "fed_h10_eur"),
    ]


def make_tail_rows():
    return [
        HistoryRow(date(2026, 7, 29), 226.649994, 0.8783, 199.06669, "fed_h10_eur"),
        HistoryRow(date(2026, 7, 30), 235.5, 0.8783, 206.83965, "fed_h10_eur"),
        HistoryRow(date(2026, 7, 31), 271.579987, 0.8783, 238.528702, "fed_h10_eur"),
    ]


def test_round_sig():
    assert round_sig(271.579987, 6) == 271.58
    assert round_sig(0.097917123, 6) == 0.0979171


def test_format_date_fr():
    assert format_date_fr(date(1997, 5, 15)) == "15 mai 1997"


def test_build_period_text():
    text = build_period_text(make_long_span_rows())
    assert text == "15 mai 1997 → 31 juillet 2026 · 3 séances"


def test_sources_note_no_active_forward_fill():
    rows = make_tail_rows()
    fx = FxRates({date(2026, 7, 31): 1.138})  # own-day quote for the last row
    note = build_sources_note(rows, fx)
    assert "utilise le taux du" not in note
    assert "utilisent le taux du" not in note
    assert note.endswith(".")


def test_sources_note_reports_active_forward_fill_block():
    rows = make_tail_rows()
    fx = FxRates({date(2026, 7, 24): 1.138})  # only a quote from a week earlier
    note = build_sources_note(rows, fx)
    assert "24 juillet 2026" in note
    assert "utilisent le taux du" in note
    assert "29 juillet 2026" in note and "31 juillet 2026" in note
