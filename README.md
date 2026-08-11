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
  via [yfinance](https://github.com/ranaroussi/yfinance) only when Stooq is
  unreachable
- FX rate: [European Central Bank](https://data.ecb.europa.eu/) reference
  rate, via their Statistical Data Warehouse API

## Disclaimer

This is a personal, non-commercial, informational project. Data is provided
as-is, with no guarantee of accuracy or timeliness, and does not constitute
financial advice. See [LICENSE](LICENSE) for the code license (MIT).
