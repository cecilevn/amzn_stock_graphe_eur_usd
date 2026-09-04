# AMZN in dollars and in euros

A chart of Amazon's stock price since its IPO (1997-05-15), in USD and
converted to EUR at the rate of the day, updated automatically on trading
days.

**Live chart:** [cecilevn.github.io/amzn_stock_graphe_eur_usd](https://cecilevn.github.io/amzn_stock_graphe_eur_usd/)

## Sources

**Historical file (1997–2026, frozen, never re-touched):**

- USD prices: [Yahoo Finance](https://finance.yahoo.com), via the GitHub repo
  [`Karthik0809/Amazon-Stock-Dashboard`](https://github.com/Karthik0809/Amazon-Stock-Dashboard) (MIT license)
- FX 1997–1998 (ECU): Federal Reserve H.10 historical archive —
  [dat96_ec.htm](https://www.federalreserve.gov/releases/h10/hist/dat96_ec.htm)
- FX 1999–2026 (Euro): Federal Reserve H.10 data — see the
  [H.10 historical data index](https://www.federalreserve.gov/releases/h10/hist/)
  (the specific historical euro-area page has since been superseded by the Fed's
  current-rate page and no longer serves the archive)

**Ongoing daily updates:**

- Prices: [Stooq](https://stooq.com) (preferred — more permissive terms for
  this kind of use), falling back to [Yahoo Finance](https://finance.yahoo.com)
  via [yfinance](https://github.com/ranaroussi/yfinance), then to
  [Nasdaq's](https://www.nasdaq.com) own historical-quote endpoint, each
  only tried when every source before it fails
- FX rate: [European Central Bank](https://data.ecb.europa.eu/) reference
  rate, via their Statistical Data Warehouse API

## Known issue: Stooq is currently blocked

Since at least 2026-08-30, Stooq's CSV endpoint returns a JavaScript
proof-of-work challenge page instead of data (an anti-bot mechanism, not
a rate limit or outage) — confirmed both from a residential IP and from
GitHub Actions runners. `fetch_stooq` raises on it and every scheduled
run currently falls back to yfinance.

This removed the intended redundancy: yfinance is documented above as
breaking a couple of times a year, which was an acceptable risk
*because* Stooq was the reliable primary source. With Stooq down, a
yfinance hiccup on 2026-09-03 and again on 2026-09-04 (an unsettled
session reported as a NaN close, caught and rejected rather than
corrupting the data — see `_reject_non_finite` in `lib/prices.py`)
stopped updates outright instead of failing over, exactly as this
section warned.

As of 2026-09-04, `fetch_new_prices` now falls back a second time, to
Nasdaq's undocumented historical-quote API (`api.nasdaq.com`, no key,
tested working) — same risk class as yfinance (an unofficial endpoint
that could itself start challenging bots or change shape without
notice), but an independent one, so the same day's yfinance hiccup and
Stooq's block don't have to coincide to be survived. If all three
sources fail, `update.py` still raises `SourceError: all price sources
failed` and the workflow fails cleanly — you'll get GitHub's
scheduled-run failure notification, and if it drags on, the
5-business-day staleness check will also fire.

## Disclaimer

This is a personal, non-commercial, informational project. Data is provided
as-is, with no guarantee of accuracy or timeliness, and does not constitute
financial advice. See [LICENSE](LICENSE) for the code license (MIT).
