"""Simple contract validator used as the starter baseline.

The implementation covers common deterministic checks:
- column presence (required_column)
- not-null constraints (not_null)
- data type validation (type)
- unique constraints (unique)
- accepted values (accepted_values)
- numeric range constraints (range)
- contract freshness checks (freshness)
- severity-aware action decisions (block/warn/pass)
"""
from __future__ import annotations

from datetime import datetime
import numbers
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml


def _issue(
    check: str,
    *,
    column: str | None,
    severity: str,
    passed: bool,
    details: str,
) -> dict[str, Any]:
    return {
        "check": check,
        "column": column,
        "severity": severity,
        "passed": bool(passed),
        "details": details,
    }


def load_contract(path: str | Path | dict[str, Any]) -> dict[str, Any]:
    if isinstance(path, dict):
        return path
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _validate_column_type(series: pd.Series, expected_type: str) -> tuple[bool, int]:
    """Kiểm tra kiểu dữ liệu cho các giá trị non-null trong series.
    
    Trả về: (passed, invalid_count)
    """
    non_null = series.dropna()
    if non_null.empty:
        return True, 0

    expected_type = expected_type.lower()

    if expected_type in ("integer", "int"):
        valid_mask = non_null.map(
            lambda value: isinstance(value, numbers.Integral)
            or (
                isinstance(value, numbers.Real)
                and not isinstance(value, (bool, np.bool_))
                and float(value).is_integer()
            )
        )
        invalid_count = int((~valid_mask).sum())
        return invalid_count == 0, invalid_count

    elif expected_type in ("number", "float", "numeric"):
        valid_mask = non_null.map(
            lambda value: isinstance(value, numbers.Real)
            and not isinstance(value, (bool, np.bool_))
        )
        invalid_count = int((~valid_mask).sum())
        return invalid_count == 0, invalid_count

    elif expected_type in ("string", "str", "text"):
        # Trong pandas, chuỗi có thể là kiểu object hoặc string
        valid_mask = non_null.map(lambda x: isinstance(x, str))
        invalid_count = int((~valid_mask).sum())
        return invalid_count == 0, invalid_count

    elif expected_type in ("datetime", "timestamp", "date"):
        dt = pd.to_datetime(non_null, errors="coerce", utc=True)
        invalid_count = int(dt.isna().sum())
        return invalid_count == 0, invalid_count

    elif expected_type in ("boolean", "bool"):
        valid_mask = non_null.map(lambda x: isinstance(x, (bool, np.bool_)))
        invalid_count = int((~valid_mask).sum())
        return invalid_count == 0, invalid_count

    return True, 0


def validate_dataframe(
    df: pd.DataFrame,
    contract: dict[str, Any],
    reference_time: datetime | pd.Timestamp | None = None,
) -> list[dict[str, Any]]:
    """Kiểm tra DataFrame dựa trên các quy tắc định nghĩa trong contract."""
    issues: list[dict[str, Any]] = []
    columns = contract.get("columns", {})

    for column, rules in columns.items():
        severity = rules.get("severity", "warning")
        required = bool(rules.get("required", False))

        # 1. Kiểm tra cột bắt buộc có tồn tại không
        if column not in df.columns:
            if required:
                issues.append(
                    _issue(
                        "required_column",
                        column=column,
                        severity=severity,
                        passed=False,
                        details=f"Missing required column: {column}",
                    )
                )
            continue

        series = df[column]

        # 2. Kiểm tra Not Null
        if required:
            null_count = int(series.isna().sum())
            issues.append(
                _issue(
                    "not_null",
                    column=column,
                    severity=severity,
                    passed=(null_count == 0),
                    details=f"null_count={null_count}",
                )
            )

        # 3. Kiểm tra Data Type
        expected_type = rules.get("type")
        if expected_type:
            type_passed, invalid_count = _validate_column_type(series, expected_type)
            issues.append(
                _issue(
                    "type",
                    column=column,
                    severity=severity,
                    passed=type_passed,
                    details=f"expected_type={expected_type}, invalid_type_count={invalid_count}",
                )
            )

        # 4. Kiểm tra Unique
        if rules.get("unique"):
            duplicate_count = int(series.duplicated(keep=False).sum())
            issues.append(
                _issue(
                    "unique",
                    column=column,
                    severity=severity,
                    passed=(duplicate_count == 0),
                    details=f"duplicate_rows={duplicate_count}",
                )
            )

        # 5. Kiểm tra Accepted Values
        accepted = rules.get("accepted_values")
        if accepted is not None:
            invalid_mask = series.notna() & ~series.isin(accepted)
            invalid_count = int(invalid_mask.sum())
            issues.append(
                _issue(
                    "accepted_values",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}; accepted={accepted}",
                )
            )

        # 6. Kiểm tra Numeric Range (Min / Max)
        if "min" in rules or "max" in rules:
            numeric = pd.to_numeric(series, errors="coerce")
            invalid = series.notna() & numeric.isna()
            if "min" in rules:
                invalid |= numeric.notna() & (numeric < rules["min"])
            if "max" in rules:
                invalid |= numeric.notna() & (numeric > rules["max"])
            invalid_count = int(invalid.sum())
            issues.append(
                _issue(
                    "range",
                    column=column,
                    severity=severity,
                    passed=(invalid_count == 0),
                    details=f"invalid_count={invalid_count}",
                )
            )

    # 7. Kiểm tra Contract Freshness
    freshness_cfg = contract.get("freshness")
    if freshness_cfg and isinstance(freshness_cfg, dict):
        col = freshness_cfg.get("column")
        max_delay = freshness_cfg.get("max_delay_minutes", 60)
        sev = freshness_cfg.get("severity", "warning")

        if not col or col not in df.columns:
            issues.append(
                _issue(
                    "freshness",
                    column=col,
                    severity=sev,
                    passed=False,
                    details=f"Missing freshness column: {col}",
                )
            )
        else:
            ts_series = pd.to_datetime(df[col], utc=True, errors="coerce").dropna()
            if ts_series.empty:
                issues.append(
                    _issue(
                        "freshness",
                        column=col,
                        severity=sev,
                        passed=False,
                        details=f"Column {col} has no valid datetime values",
                    )
                )
            else:
                latest_ts = ts_series.max()
                now_ts = (
                    pd.Timestamp(reference_time)
                    if reference_time is not None
                    else pd.Timestamp.now(tz="UTC")
                )
                if now_ts.tzinfo is None:
                    now_ts = now_ts.tz_localize("UTC")
                else:
                    now_ts = now_ts.tz_convert("UTC")
                delay_minutes = (now_ts - latest_ts).total_seconds() / 60.0
                passed = delay_minutes <= max_delay
                issues.append(
                    _issue(
                        "freshness",
                        column=col,
                        severity=sev,
                        passed=passed,
                        details=f"delay_minutes={delay_minutes:.1f}, max_delay={max_delay}",
                    )
                )

    return issues


def failed_issues(issues: list[dict[str, Any]], min_severity: str | None = None) -> list[dict[str, Any]]:
    failed = [i for i in issues if not i.get("passed", False)]
    if min_severity is None:
        return failed
    order = {"info": 0, "warning": 1, "critical": 2}
    threshold = order.get(min_severity, 1)
    return [i for i in failed if order.get(i.get("severity", "warning"), 1) >= threshold]


def determine_action(issues: list[dict[str, Any]]) -> str:
    """Xác định hành động của pipeline dựa trên mức độ lỗi:
    - 'block': khi có lỗi critical
    - 'warn': khi chỉ có lỗi warning
    - 'pass': khi không có lỗi hoặc chỉ có info
    """
    failed = [i for i in issues if not i.get("passed", False)]
    if not failed:
        return "pass"
    severities = {i.get("severity", "warning") for i in failed}
    if "critical" in severities:
        return "block"
    if "warning" in severities:
        return "warn"
    return "pass"
