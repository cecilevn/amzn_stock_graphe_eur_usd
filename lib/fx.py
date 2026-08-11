"""ECB EUR/USD reference rates, with forward-fill for non-quoted sessions.

Uses the ECB's Statistical Data Warehouse REST API (data-api.ecb.europa.eu),
not the static eurofxref-hist.csv export on www.ecb.europa.eu: that export
sits behind Myra Cloud bot mitigation, which serves fabricated data to
non-browser clients instead of an honest block — confirmed independently
from two unrelated networks, see project memory. The REST API is not
behind that protection and returns genuine, officially labelled rates.

The ECB publishes dollars-per-euro (~1.14). This module inverts that to
euros-per-dollar to match the history.csv convention. Rates are never
interpolated: a trading session without its own ECB quote reuses the
latest earlier quote, never a future one.
"""

from __future__ import annotations

import bisect
import csv
import io
from datetime import date

import requests

ECB_API_URL = "https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
REQUEST_TIMEOUT = 30


class FxRates:
    """USD-per-EUR rates keyed by date, from the ECB."""

    def __init__(self, usd_per_eur: dict[date, float]):
        if not usd_per_eur:
            raise ValueError("FxRates needs at least one rate")
        self._usd_per_eur = usd_per_eur
        self._sorted_dates = sorted(usd_per_eur)

    def eur_per_usd_asof(self, session: date) -> tuple[float, date]:
        """Return (eur_per_usd, rate_date) for a trading session.

        Uses the session's own ECB quote if there is one, otherwise the
        latest quote on or before that date (forward-fill).
        """
        if session in self._usd_per_eur:
            rate_date = session
        else:
            idx = bisect.bisect_right(self._sorted_dates, session)
            if idx == 0:
                raise ValueError(f"no ECB rate on or before {session}")
            rate_date = self._sorted_dates[idx - 1]
        usd_per_eur = self._usd_per_eur[rate_date]
        return round(1.0 / usd_per_eur, 6), rate_date


def fetch_ecb_rates(start: date, end: date) -> FxRates:
    """Fetch USD-per-EUR rates for [start, end] from the ECB's SDW API.

    Callers should pad `start` with a buffer before the date they
    actually need (see update.py): this queries a window, not the full
    history, so the window must be wide enough to resolve every date
    that will be looked up against the result.
    """
    resp = requests.get(
        ECB_API_URL,
        params={"format": "csvdata", "startPeriod": start.isoformat(), "endPeriod": end.isoformat()},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()

    reader = csv.DictReader(io.StringIO(resp.text))
    if not reader.fieldnames or "TIME_PERIOD" not in reader.fieldnames or "OBS_VALUE" not in reader.fieldnames:
        raise RuntimeError(f"ecb: unexpected columns: {reader.fieldnames}")

    rates: dict[date, float] = {}
    for record in reader:
        raw = (record.get("OBS_VALUE") or "").strip()
        if not raw:
            continue
        rates[date.fromisoformat(record["TIME_PERIOD"].strip())] = float(raw)

    if not rates:
        raise RuntimeError(f"ecb: no usable rates parsed for [{start}, {end}]")
    return FxRates(rates)
