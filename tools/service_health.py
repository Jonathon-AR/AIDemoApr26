"""
Queries ESB business KPIs from esb.csv.
Detects anomalies: success_rate < 1.0 or avg_time spike (>2× rolling median).
"""
import pandas as pd
from config import ESB_FILE

_cache: dict = {}

_BASELINE_WINDOW = 10  # minutes for rolling median baseline


def _load() -> pd.DataFrame:
    if "df" not in _cache:
        df = pd.read_csv(ESB_FILE)
        df = df.sort_values("startTime").reset_index(drop=True)
        # rolling median of avg_time for anomaly detection
        df["_avg_time_median"] = (
            df["avg_time"].rolling(_BASELINE_WINDOW, min_periods=1).median()
        )
        _cache["df"] = df
    return _cache["df"]


def get_service_health(service_name: str, start_ts: int, end_ts: int) -> dict:
    """
    Returns per-minute ESB KPIs for a service in the given time window.

    Args:
        service_name: ESB service identifier, e.g. "osb_001".
        start_ts:     Window start (Unix milliseconds, UTC).
        end_ts:       Window end   (Unix milliseconds, UTC).

    Returns:
        Dict with keys:
          - service: str
          - window_start / window_end: Unix ms
          - buckets: list of per-minute dicts
          - anomalies: list of buckets where success_rate < 1 or latency spiked
          - summary: high-level stats (total_calls, overall_success_rate, peak_avg_time_ms)
    """
    df = _load()
    mask = (
        (df["serviceName"] == service_name)
        & (df["startTime"] >= start_ts)
        & (df["startTime"] <= end_ts)
    )
    window = df[mask].copy()

    if window.empty:
        return {
            "service": service_name,
            "window_start": start_ts,
            "window_end": end_ts,
            "buckets": [],
            "anomalies": [],
            "summary": None,
        }

    buckets = []
    anomalies = []
    for _, row in window.iterrows():
        is_rate_anomaly = row["succee_rate"] < 1.0
        is_latency_anomaly = (
            row["_avg_time_median"] > 0
            and row["avg_time"] > 2 * row["_avg_time_median"]
        )
        bucket = {
            "startTime_ms":  int(row["startTime"]),
            "avg_time_ms":   round(float(row["avg_time"]), 4),
            "num_calls":     int(row["num"]),
            "success_num":   int(row["succee_num"]),
            "success_rate":  round(float(row["succee_rate"]), 4),
            "anomaly":       is_rate_anomaly or is_latency_anomaly,
        }
        buckets.append(bucket)
        if bucket["anomaly"]:
            anomalies.append(bucket)

    total_calls = sum(b["num_calls"] for b in buckets)
    total_success = sum(b["success_num"] for b in buckets)

    return {
        "service":        service_name,
        "window_start":   start_ts,
        "window_end":     end_ts,
        "buckets":        buckets,
        "anomalies":      anomalies,
        "summary": {
            "total_calls":          total_calls,
            "overall_success_rate": round(total_success / total_calls, 4) if total_calls else None,
            "peak_avg_time_ms":     round(max(b["avg_time_ms"] for b in buckets), 4),
            "anomaly_bucket_count": len(anomalies),
        },
    }
