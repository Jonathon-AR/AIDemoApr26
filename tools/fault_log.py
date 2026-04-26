"""
Reads the fault incident log (0_fault_description.xlsx).
Fault timestamps are stored as CST (UTC+8); all outputs use UTC Unix ms.
"""
from datetime import datetime, timezone, timedelta
import pandas as pd
from config import FAULT_FILE, CST_OFFSET_HOURS

_CST = timezone(timedelta(hours=CST_OFFSET_HOURS))
_cache: dict = {}


def _load() -> pd.DataFrame:
    if "df" not in _cache:
        df = pd.read_excel(FAULT_FILE)
        # parse start_time as CST-aware and convert to UTC Unix ms
        df["start_ts_utc_ms"] = df["start_time"].apply(
            lambda v: int(
                datetime.strptime(str(v), "%Y-%m-%d %H:%M:%S")
                .replace(tzinfo=_CST)
                .timestamp()
                * 1000
            )
        )
        # parse duration string like "5min" → integer minutes
        df["duration_min"] = df["duration"].str.extract(r"(\d+)").astype(int)
        df["end_ts_utc_ms"] = df["start_ts_utc_ms"] + df["duration_min"] * 60_000
        _cache["df"] = df
    return _cache["df"]


def get_fault_log(fault_id: int | None = None) -> list[dict]:
    """
    Returns known fault incidents from the ground-truth log.

    Args:
        fault_id: if provided, return only that incident; otherwise return all.

    Returns:
        List of dicts with keys: fault_id, start_ts_utc_ms, end_ts_utc_ms,
        duration_min, start_time_utc (ISO string).
    """
    df = _load()
    if fault_id is not None:
        df = df[df["fault_id"] == fault_id]

    results = []
    for _, row in df.iterrows():
        start_dt = datetime.fromtimestamp(row["start_ts_utc_ms"] / 1000, tz=timezone.utc)
        results.append({
            "fault_id":        int(row["fault_id"]),
            "start_ts_utc_ms": int(row["start_ts_utc_ms"]),
            "end_ts_utc_ms":   int(row["end_ts_utc_ms"]),
            "duration_min":    int(row["duration_min"]),
            "start_time_utc":  start_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
        })
    return results
