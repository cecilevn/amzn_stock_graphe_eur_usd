from datetime import date

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


def test_fetch_new_prices_raises_when_both_sources_fail(monkeypatch):
    monkeypatch.setattr(prices, "fetch_stooq", lambda since: (_ for _ in ()).throw(prices.SourceError("stooq: blocked")))
    monkeypatch.setattr(prices, "fetch_yfinance", lambda since: (_ for _ in ()).throw(prices.SourceError("yfinance: network error")))

    with pytest.raises(prices.SourceError, match="both price sources failed"):
        prices.fetch_new_prices(date(2026, 8, 11))


def test_fetch_yfinance_empty_history_returns_no_rows(monkeypatch):
    import yfinance as yf

    class FakeEmptyHist:
        def iterrows(self):
            return iter(())

    monkeypatch.setattr(yf, "Ticker", lambda symbol: type("T", (), {"history": lambda self, **kw: FakeEmptyHist()})())
    assert prices.fetch_yfinance(date(2026, 8, 11)) == []
