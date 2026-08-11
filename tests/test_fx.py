from datetime import date

import pytest

from lib.fx import FxRates


def make_fx() -> FxRates:
    return FxRates({
        date(2026, 8, 3): 1.10,  # Monday, real quote
        date(2026, 8, 4): 1.11,  # Tuesday
        date(2026, 8, 7): 1.12,  # Friday (Wed/Thu missing, e.g. a holiday)
    })


def test_own_day_rate_used_when_available():
    fx = make_fx()
    rate, rate_date = fx.eur_per_usd_asof(date(2026, 8, 4))
    assert rate_date == date(2026, 8, 4)
    assert rate == pytest.approx(round(1 / 1.11, 6))


def test_forward_fill_carries_last_known_rate_without_interpolating():
    fx = make_fx()
    rate, rate_date = fx.eur_per_usd_asof(date(2026, 8, 5))  # Wednesday, no quote
    assert rate_date == date(2026, 8, 4)  # carried from Tuesday, not interpolated toward Friday
    assert rate == pytest.approx(round(1 / 1.11, 6))

    rate2, rate_date2 = fx.eur_per_usd_asof(date(2026, 8, 6))  # Thursday, still no quote
    assert rate_date2 == date(2026, 8, 4)
    assert rate2 == rate


def test_never_looks_into_the_future():
    fx = make_fx()
    with pytest.raises(ValueError):
        fx.eur_per_usd_asof(date(2026, 8, 1))  # before the earliest known rate
