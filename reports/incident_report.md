# Incident Report — Data Quality Degradation (Duplicate PK & Volume Drop)

## Severity
**P1 — High Severity** (Ảnh hưởng trực tiếp đến tính đúng đắn của doanh thu báo cáo cho Ban Giám Đốc).

## Summary
Hệ thống phát hiện các sự cố dữ liệu trong luồng ingestion:
1. Bị trùng lặp khóa chính `order_id` dẫn đến vi phạm data contract nghiêm trọng.
2. Sụt giảm số lượng đơn hàng (volume drop 75%) do sự cố kết nối upstream API.

## Detection
- **Signal**:
  - `contract_validator`: Failed check `unique` trên cột `order_id` (Severity: `critical`).
  - `anomaly_detector`: `row-count anomaly` kích hoạt với score > 7.0 (Z-score / MAD).
  - `slo_status`: Burn rate đạt mức cao, vi phạm budget.
- **First observed time**: 2026-08-29T11:48:58Z

## Root Cause
1. **Duplicate PK**: Upstream webhook gửi retry nhiều lần cho cùng 1 batch mà không có cơ chế idempotency.
2. **Volume Drop**: Quá trình ingestion ngắt quãng làm chỉ lấy được 150/600 bản ghi.

## Evidence
1. `reports/latest_metrics.json` ghi nhận `critical_contract_failures = 1` và `failed_contract_checks = 1`.
2. Output kiểm tra contract báo: `check="unique", column="order_id", duplicate_rows=6`.
3. `row-count anomaly` ghi nhận score bất thường so với dữ liệu lịch sử 14 ngày trước đó.

## Blast Radius
```text
stg_orders (Order Ingestion)
  └── fct_daily_revenue (Daily Aggregation Mart)
        └── ceo_revenue_dashboard (Executive Dashboard)
```
- **Tác động**: Gây sai lệch (thổi phồng hoặc hụt giảm nghiêm trọng) chỉ số `daily_revenue` và `completed_order_rows` trên CEO Dashboard.

## Mitigation
1. **Data Contract Enforcement**: Áp dụng action `block` tự động dừng pipeline khi phát hiện lỗi `critical` (`duplicate_pk`), không cho dữ liệu bẩn load vào data mart `fct_daily_revenue`.
2. **Alerting**: Kích hoạt cảnh báo multi-window burn rate tới đội ngũ On-call Data Engineer.

## Recovery
1. Chạy `python scripts/reset_lab.py` để làm sạch dữ liệu nguồn và re-ingest dữ liệu chuẩn.
2. Thực hiện `dbt build` lại toàn bộ staging và marts.

## Verification
- [x] Contract healthy (`critical_contract_fails = 0`)
- [x] dbt tests healthy (`dbt test` pass 100%)
- [x] Anomaly returned to expected range (`is_anomaly = False`)
- [x] SLO healthy / budget understood (`burn_rate` ổn định)
- [x] Downstream output verified (`fct_daily_revenue` phản ánh đúng số doanh thu)

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Bật Contract Validator tự động trước khi load vào Warehouse | Data Platform | Q3-2026 | Chặn lỗi duplicate và sai type ngay tại cửa ngõ |
| Thêm dbt unit test kiểm tra duplicate customer join | Analytics Eng | Q3-2026 | Ngăn ngừa revenue inflation |
| Triển khai Multi-window burn rate alert trên Slack/PagerDuty | SRE/Observability | Q3-2026 | Giảm false alarm do transient spikes |
