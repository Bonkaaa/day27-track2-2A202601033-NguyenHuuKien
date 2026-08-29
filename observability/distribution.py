from __future__ import annotations

from typing import Any, Iterable

import numpy as np
from scipy import stats


def detect_distribution_shift(
    current_values: Iterable[float],
    baseline_values: Iterable[float],
    *,
    ratio_threshold: float = 3.0,
    pvalue_threshold: float = 0.01,
) -> dict[str, Any]:
    """Detect distribution shifts using both Kolmogorov-Smirnov test and mean ratio."""
    cur = np.asarray(list(current_values), dtype=float)
    base = np.asarray(list(baseline_values), dtype=float)
    if cur.size == 0 or base.size == 0:
        return {"is_anomaly": False, "score": 0.0, "method": "distribution_shift", "reason": "empty_input"}

    cur_mean = float(np.mean(cur))
    base_mean = float(np.mean(base))

    # 1. Mean ratio score
    if base_mean == 0:
        mean_score = float("inf") if cur_mean != 0 else 1.0
    else:
        mean_score = max(abs(cur_mean / base_mean), abs(base_mean / cur_mean)) if cur_mean != 0 else float("inf")

    # 2. 2-Sample Kolmogorov-Smirnov Test
    ks_res = stats.ks_2samp(cur, base)
    ks_stat = float(ks_res.statistic)
    ks_pvalue = float(ks_res.pvalue)

    # Anomaly if mean ratio >= ratio_threshold OR KS test p-value is extremely small with significant stat
    is_anomaly = bool((mean_score >= ratio_threshold) or (ks_pvalue < pvalue_threshold and ks_stat >= 0.4))
    score = float(max(mean_score if mean_score != float("inf") else 100.0, ks_stat * 10))

    return {
        "is_anomaly": is_anomaly,
        "score": score,
        "method": "ks_and_mean_ratio",
        "ks_statistic": ks_stat,
        "ks_pvalue": ks_pvalue,
        "mean_ratio": mean_score,
        "reason": f"baseline_mean={base_mean:.3f}, current_mean={cur_mean:.3f}, ks_pvalue={ks_pvalue:.4e}",
    }
