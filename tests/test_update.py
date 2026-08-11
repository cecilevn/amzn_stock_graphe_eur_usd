from datetime import date

from update import business_days_since


def test_zero_gap_same_day():
    assert business_days_since(date(2026, 8, 10), date(2026, 8, 10)) == 0


def test_counts_weekdays_only():
    # Monday to the following Monday: Tue, Wed, Thu, Fri, Mon = 5 weekdays.
    assert business_days_since(date(2026, 8, 3), date(2026, 8, 10)) == 5


def test_weekend_gap_does_not_count():
    # Friday to Monday: no weekday in between.
    assert business_days_since(date(2026, 8, 7), date(2026, 8, 10)) == 1
