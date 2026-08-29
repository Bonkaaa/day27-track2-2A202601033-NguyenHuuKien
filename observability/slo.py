from __future__ import annotations

from typing import Any


def calculate_slo(target: float, bad_events: int, total_events: int) -> dict[str, Any]:
    if not 0 < target < 1:
        raise ValueError("target must be between 0 and 1 (exclusive)")
    if bad_events < 0 or total_events < 0 or bad_events > total_events:
        raise ValueError("invalid event counts")
    allowed_bad_rate = 1.0 - target
    if total_events == 0:
        return {
            "target": target,
            "actual_bad_rate": 0.0,
            "allowed_bad_rate": allowed_bad_rate,
            "burn_rate": 0.0,
            "remaining_error_budget_fraction": 1.0,
            "breached": False,
        }
    actual_bad_rate = bad_events / total_events
    burn_rate = actual_bad_rate / allowed_bad_rate
    consumed_fraction = min(1.0, actual_bad_rate / allowed_bad_rate)
    return {
        "target": target,
        "actual_bad_rate": actual_bad_rate,
        "allowed_bad_rate": allowed_bad_rate,
        "burn_rate": burn_rate,
        "remaining_error_budget_fraction": max(0.0, 1.0 - consumed_fraction),
        "breached": bool(actual_bad_rate > allowed_bad_rate),
    }


def evaluate_multiwindow_burn(
    *,
    short_window_burn: float,
    long_window_burn: float,
    policy: str = "starter",
) -> dict[str, Any]:
    """Đánh giá chính sách burn rate đa cửa sổ (Multi-window multi-burn-rate)."""
    
    # 1. Sustained Fast Burn (Cả short và long đều cháy nhanh -> Cần Page khẩn cấp)
    # Ví dụ: tiêu chuẩn SRE cho 1h/6h với burn rate >= 14.4 hoặc >= 5.0
    if short_window_burn >= 5.0 and long_window_burn >= 2.0:
        return {
            "page": True,
            "severity": "critical",
            "reason": "sustained_fast_burn",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    # 2. Transient Spike (Chỉ short cao, long thấp -> Cảnh báo nhưng không làm phiền on-call ban đêm)
    if short_window_burn >= 5.0 and long_window_burn < 2.0:
        return {
            "page": False,
            "severity": "warning",
            "reason": "transient_spike_ignored_for_paging",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    # 3. Slow Burn / Normal
    if long_window_burn >= 1.0:
        return {
            "page": False,
            "severity": "warning",
            "reason": "slow_burn_create_ticket",
            "short_window_burn": short_window_burn,
            "long_window_burn": long_window_burn,
        }

    return {
        "page": False,
        "severity": "info",
        "reason": "burn_rate_healthy",
        "short_window_burn": short_window_burn,
        "long_window_burn": long_window_burn,
    }

