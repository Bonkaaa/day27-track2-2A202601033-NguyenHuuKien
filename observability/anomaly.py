"""Anomaly detection starter.

Z-score is deliberately the default baseline. Students should improve `auto`
mode for seasonality/outliers rather than deleting the simple implementation.
"""
from __future__ import annotations

from typing import Any, Iterable

import numpy as np


def zscore_detector(current: float, history: Iterable[float], threshold: float = 3.0) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    if values.size < 3:
        return {"is_anomaly": False, "score": 0.0, "method": "zscore", "reason": "insufficient_history"}
    mean = float(np.mean(values))
    std = float(np.std(values))
    if std == 0:
        score = float("inf") if float(current) != mean else 0.0
    else:
        score = abs(float(current) - mean) / std
    return {
        "is_anomaly": bool(score > threshold),
        "score": float(score),
        "method": "zscore",
        "reason": f"mean={mean:.3f}, std={std:.3f}, threshold={threshold}",
    }


def mad_detector(current: float, history: Iterable[float], threshold: float = 3.5) -> dict[str, Any]:
    values = np.asarray(list(history), dtype=float)
    if values.size < 5:
        return {"is_anomaly": False, "score": 0.0, "method": "mad", "reason": "insufficient_history"}
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    
    if mad == 0:
        # Nếu mad = 0, kiểm tra xem current có bằng median không
        diff = abs(float(current) - median)
        is_anom = diff > 0
        score = float("inf") if is_anom else 0.0
        return {
            "is_anomaly": is_anom,
            "score": score,
            "method": "mad",
            "reason": f"median={median:.3f}, mad=0 (zero variance), diff={diff:.3f}",
        }
    
    modified_z = 0.6745 * abs(float(current) - median) / mad
    return {
        "is_anomaly": bool(modified_z > threshold),
        "score": float(modified_z),
        "method": "mad",
        "reason": f"median={median:.3f}, mad={mad:.3f}, threshold={threshold}",
    }



def detect_anomaly(
    current: float,
    history: Iterable[float],
    *,
    method: str = "auto",
    threshold: float = 3.0,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stable lab API.

    Current starter behavior:
    - `zscore`: basic z-score.
    - `mad`: MAD example.
    - `auto`: still uses naive z-score and ignores context.

    TODO(student): make `auto` context-aware. Useful context keys used by the
    instructor may include `day_of_week`, `same_segment_history`,
    `metric_name`, `known_event`, and `trend`.
    """
    if method == "mad":
        return mad_detector(current, history)
        
    if method == "auto":
        # Sử dụng segment history từ context nếu có
        effective_history = history
        if context and "same_segment_history" in context:
            effective_history = context["same_segment_history"]

        vals = list(effective_history)
        if len(vals) >= 5:
            res = mad_detector(current, vals, threshold=3.5)
            res["method"] = "auto:mad"
            return res
        else:
            res = zscore_detector(current, vals, threshold=threshold)
            res["method"] = "auto:zscore"
            return res

    if method == "zscore":
        return zscore_detector(current, history, threshold=threshold)
        
    raise ValueError(f"Unsupported method: {method}")


