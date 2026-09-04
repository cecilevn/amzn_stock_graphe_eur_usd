from datetime import date, datetime

import pytest

from lib import prices


def test_fetch_new_prices_falls_back_to_yfinance_on_stooq_failure(monkeypatch):
    monkeypatch.setattr(prices, "fetch_stooq", lambda since: (_ for _ in ()).throw(prices.SourceError("stooq: blocked")))
    monkeypatch.setattr(prices, "fetch_yfinance", lambda since: [prices.PriceRow(date(2026, 8, 4), 280.0)])

    rows, source = prices.fetch_new_prices(date(2026, 8, 3))
    assert source == "yfinance"
    assert rows == [prices.PriceRow(date(2026, 8, 4), 280.0)]


def test_fetch_new_prices_no_new_session_is_not_an_error(monkeypatch):
    """Regression: Stooq blocked + yfinance genuinely has nothing newer
    than `since` yet must not be treated as a fetch failure (this crashed
    a real workflow run before the fix)."""
    monkeypatch.setattr(prices, "fetch_stooq", lambda since: (_ for _ in ()).throw(prices.SourceError("stooq: blocked")))
    monkeypatch.setattr(prices, "fetch_yfinance", lambda since: [])

    rows, source = prices.fetch_new_prices(date(2026, 8, 11))
    assert rows == []
    assert source == "yfinance"


def test_fetch_new_prices_falls_back_to_nasdaq_when_stooq_and_yfinance_fail(monkeypatch):
    """Regression: Stooq's anti-bot block (2026-09) plus a transient
    yfinance hiccup (unsettled-session NaN) must not stop updates
    entirely — Nasdaq is a third, independent fallback."""
    monkeypatch.setattr(prices, "fetch_stooq", lambda since: (_ for _ in ()).throw(prices.SourceError("stooq: blocked")))
    monkeypatch.setattr(prices, "fetch_yfinance", lambda since: (_ for _ in ()).throw(prices.SourceError("yfinance: non-finite close")))
    monkeypatch.setattr(prices, "fetch_nasdaq", lambda since: [prices.PriceRow(date(2026, 8, 4), 280.0)])

    rows, source = prices.fetch_new_prices(date(2026, 8, 3))
    assert source == "nasdaq"
    assert rows == [prices.PriceRow(date(2026, 8, 4), 280.0)]


def test_fetch_new_prices_raises_when_all_sources_fail(monkeypatch):
    monkeypatch.setattr(prices, "fetch_stooq", lambda since: (_ for _ in ()).throw(prices.SourceError("stooq: blocked")))
    monkeypatch.setattr(prices, "fetch_yfinance", lambda since: (_ for _ in ()).throw(prices.SourceError("yfinance: network error")))
    monkeypatch.setattr(prices, "fetch_nasdaq", lambda since: (_ for _ in ()).throw(prices.SourceError("nasdaq: network error")))

    with pytest.raises(prices.SourceError, match="all price sources failed"):
        prices.fetch_new_prices(date(2026, 8, 11))


def test_reject_non_finite_raises_on_nan_close():
    """Regression: yfinance sometimes reports a NaN close for a session
    that hasn't settled yet. Writing that to history.csv crashes the
    render step and gets committed anyway — must be treated as a failure
    of that source instead."""
    with pytest.raises(prices.SourceError, match="non-finite close"):
        prices._reject_non_finite([prices.PriceRow(date(2026, 8, 4), float("nan"))], "yfinance")


def test_fetch_yfinance_raises_on_nan_close(monkeypatch):
    import yfinance as yf

    class FakeHist:
        def iterrows(self):
            yield datetime(2026, 8, 4), {"Close": float("nan")}

    monkeypatch.setattr(yf, "Ticker", lambda symbol: type("T", (), {"history": lambda self, **kw: FakeHist()})())

    with pytest.raises(prices.SourceError, match="non-finite close"):
        prices.fetch_yfinance(date(2026, 8, 3))


def test_fetch_yfinance_empty_history_returns_no_rows(monkeypatch):
    import yfinance as yf

    class FakeEmptyHist:
        def iterrows(self):
            return iter(())

    monkeypatch.setattr(yf, "Ticker", lambda symbol: type("T", (), {"history": lambda self, **kw: FakeEmptyHist()})())
    assert prices.fetch_yfinance(date(2026, 8, 11)) == []


def _fake_nasdaq_response(rows):
    class FakeResponse:
        text = "{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {"data": {"tradesTable": {"rows": rows}}}

    return FakeResponse()


def test_fetch_nasdaq_parses_dollar_amounts_and_us_dates(monkeypatch):
    monkeypatch.setattr(
        prices.requests,
        "get",
        lambda url, params, headers, timeout: _fake_nasdaq_response(
            [{"date": "09/03/2026", "close": "$258.90"}, {"date": "09/02/2026", "close": "$254.98"}]
        ),
    )
    rows = prices.fetch_nasdaq(date(2026, 9, 2))
    assert rows == [prices.PriceRow(date(2026, 9, 3), 258.90)]


def test_fetch_nasdaq_raises_on_unexpected_body(monkeypatch):
    class FakeResponse:
        text = "<!DOCTYPE html>not json"

        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("not json")

    monkeypatch.setattr(prices.requests, "get", lambda url, params, headers, timeout: FakeResponse())
    with pytest.raises(prices.SourceError, match="unexpected response body"):
        prices.fetch_nasdaq(date(2026, 9, 2))
