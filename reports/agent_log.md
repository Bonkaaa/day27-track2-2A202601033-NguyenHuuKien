# AI Agent Decision Log

## Decision 1 — Contract Validation & Severity Actions (Phase 1)
- **Hypothesis**: Cần kiểm tra chặt chẽ kiểu dữ liệu, freshness và phân loại mức độ nghiêm trọng để quyết định hành động cho pipeline.
- **Prompt / request to agent**: Hướng dẫn hoàn thiện hàm `validate_dataframe` và logic kiểm tra type, freshness, action matrix.
- **Agent proposal**: 
  - Tách hàm `_validate_column_type` riêng cho int, float, string, datetime, bool.
  - Tính toán freshness trễ bao nhiêu phút so với UTC timestamp hiện tại.
  - Hàm `determine_action` trả về `block` khi có lỗi `critical`, `warn` khi có lỗi `warning`.
- **Evidence/test**: Bộ test `tests_public/test_contracts.py` pass 100% khi test với `duplicate_pk`, `stale_data`, `invalid_type`.
- **Accept / reject / revise**: **Accept**.
- **Why**: Giúp hệ thống tự động bảo vệ Warehouse ngay từ tầng Ingestion.

---

## Decision 2 — dbt Transformation Testing vs Unit Testing (Phase 2)
- **Hypothesis**: Cần phân biệt Data Test (chạy trên data thật) và Unit Test (chạy trên mock fixture) để bảo vệ logic tính doanh thu.
- **Prompt / request to agent**: Thêm Generic Data tests, Singular test và Unit test phát hiện bug Revenue Inflation khi duplicate active customer.
- **Agent proposal**:
  - Thêm `unique` và `not_null` cho `order_date`, `completed_order_rows`.
  - Viết singular test `assert_daily_orders_positive.sql`.
  - Viết `unit_tests.yml` mô phỏng 1 customer có 2 dòng `is_active = true` để chứng minh lỗi nhân đôi doanh thu của phép `left join`.
- **Evidence/test**: `dbt build` chạy thành công các data tests và expose đúng thất bại của unit test duplicate customer.
- **Accept / reject / revise**: **Accept**.
- **Why**: Giúp phát hiện lỗi logic SQL ngay trong quá trình CI/CD mà không cần database thật.

---

## Decision 3 — Robust Anomaly Detection (Phase 3)
- **Hypothesis**: Z-score dễ bị đánh lừa bởi outliers và dữ liệu phân phối lệch.
- **Prompt / request to agent**: Cải tiến `detect_anomaly(method="auto")` để xử lý ngoại lai và dữ liệu có phương sai bằng 0.
- **Agent proposal**: Cài đặt thuật toán Median Absolute Deviation (MAD) làm mặc định cho `auto` khi có $\ge 5$ điểm dữ liệu lịch sử, xử lý ngoại lệ `mad == 0` (Zero Variance).
- **Evidence/test**: Bắt thành công lỗi `volume_drop` trong baseline metrics và pass `tests_public/test_anomaly.py`.
- **Accept / reject / revise**: **Accept**.
- **Why**: Tăng tính ổn định và giảm thiểu cảnh báo giả.

---

## Decision 4 — Multi-Window Multi-Burn-Rate Alerting (Phase 5)
- **Hypothesis**: Cảnh báo đơn lẻ theo thời gian thực dễ gây báo động giả khi có transient spike ngắn.
- **Prompt / request to agent**: Xây dựng hàm `evaluate_multiwindow_burn` theo chuẩn Google SRE.
- **Agent proposal**: Chỉ gửi cảnh báo khẩn cấp (`page=True`) khi cả 2 cửa sổ (short window và long window) đều vượt ngưỡng burn rate.
- **Evidence/test**: Unit test `test_transient_spike_does_not_page` và `test_sustained_fast_burn_triggers_paging` pass.
- **Accept / reject / revise**: **Accept**.
- **Why**: Giảm mệt mỏi cho đội ngũ on-call (Alert Fatigue) trong khi vẫn đảm bảo bắt được các sự cố nghiêm trọng.
