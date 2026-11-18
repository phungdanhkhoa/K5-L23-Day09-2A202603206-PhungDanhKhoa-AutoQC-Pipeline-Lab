# Báo cáo Day 09 — Phùng Danh Khoa · 2A202603206

## 1. Kết luận

**Hold.** Cửa nhận giữ 205/224 ảnh, loại 19. Sau sửa tự động và duyệt mô phỏng 80 ảnh, còn **0 lỗi bắt buộc** và **64/205 ảnh (31,22%)** có cảnh báo chưa duyệt, vượt ngưỡng 10%. Pipeline xuất 205 ảnh vào [bản nháp clean_v1](export/clean_v1/manifest.json) để thử nghiệm. Quyết định và số liệu nằm trong [08_summary.json](reports/08_summary.json).

## 2. Lỗi và phân việc

[Danh sách v1](reports/02_error_list_v1.csv) có 455 dòng báo cáo: 19 lỗi cửa nhận trên 224 ảnh và 436 mục QC trên 205 ảnh được nhận, gồm 36 lỗi bắt buộc và 400 cảnh báo. Các lỗi theo dòng được tính trên 675 dòng nhãn khác rỗng trước sửa.

| Mã lỗi | Số lượng | Xử lý |
|---|---|---|
| `DUP_IMAGE_EXACT`, `DUP_IMAGE_NEAR`, `LEAK_TEST` | 8, 2, 4 ảnh / 224 | Máy loại trùng và ngăn rò rỉ ở cửa nhận |
| `CORRUPT_IMAGE`, `BAD_SIZE` | 2, 3 ảnh / 224 | Máy loại ảnh không giải mã được hoặc thiếu độ phân giải |
| `BAD_CLASS_ID`, `BAD_FORMAT`, `BOX_ZERO`, `DUP_BOX` | 6, 3, 4, 7 dòng / 675 | Máy bỏ 20 dòng, lưu dòng gốc trong log |
| `BOX_OUT_OF_IMAGE` | 8 dòng / 675 | Máy cắt box theo biên và giữ ID lớp |
| `BAD_CLASS_NAME` | 2 tên / 4 lớp | Máy sửa một lần trường `names` |
| `MISSING_LABEL_FILE` | 6 ảnh / 205 | Người gán. Máy ghi `needs_label` và giữ nguyên trạng thái thiếu |
| `POSSIBLE_MISSING`, `POSSIBLE_LOOSE_BOX` | 267 cờ trên 97 ảnh và 60 cờ trên 46 ảnh / 205 | Người xác minh vật bỏ sót và biên box |
| `POSSIBLE_WRONG_CLASS`, `POSSIBLE_FALSE_POS` | 23 cờ trên 22 ảnh và 25 cờ trên 24 ảnh / 205 | Người đối chiếu vật, lớp và dự đoán |
| `EMPTY_LABEL`, `BOX_TINY`, `BOX_HUGE` | 12 ảnh / 205, 6 và 3 dòng / 675 | Người phân biệt ảnh nền, vật nhỏ hợp lệ và box sai |
| `CLASS_RARE` | 4 token hiếm toàn lô | Kiểm tra thống kê sau khi máy loại ID/dòng sai |

[Audit sửa tự động](reports/03_fixes.csv) có 29 thay đổi và 6 mục chuyển người. Trong [hàng đợi](reports/05_review_queue.csv), `img_0160` đứng đầu (109,727 điểm) vì nhiều cờ thiếu vật và khác lớp. Điểm cộng dồn trọng số theo mã, có nhân theo confidence với cờ dự đoán. Sáu ảnh cần gán có 10 điểm/ảnh, ở vị trí 34–39. [Duyệt mô phỏng](reports/06_review_log.csv) xử lý 80/149 ảnh trong hàng, bao phủ 301/374 cờ ngữ nghĩa v2 (231 thiếu, 35 lỏng, 21 khác lớp, 14 nghi thừa). Số này đo độ bao phủ hàng đợi, còn xác nhận lỗi cần người mở ảnh.

## 3. Calibration trên 39 ảnh

| Ngưỡng | Trước → sau | Precision / recall trước → sau | Cơ sở chọn |
|---|---|---|---|
| `duplicates.phash_dist` | 2 → **4** | Gần trùng 1,00 / 0,50 → 1,00 / 0,67. Trùng byte vẫn 1,00 / 1,00 | Bắt thêm 1/6 ca gần trùng, 0 FP. Từ 6 đến 14 không tăng recall. Giữ 4 để hạn chế gộp nhầm ảnh sẽ bị loại tự động |
| `second_opinion.conf` | 0,25 → **0,10** | Thiếu box 0,50 / 1,00 → 0,40 / 1,00. Box lỏng 0,29 / 0,40 → 0,38 / 0,60 | Bắt thêm 1/5 ca box lỏng và giữ 8/8 ca thiếu, đổi lấy 4 FP thiếu box (8 → 12). Khác lớp giữ 0,56 / 0,83. Nghi thừa giữ 0,36 / 1,00 vì dùng `fp_conf` riêng |

[Xem hai sweep](calibration/calibration_report.md). Tăng pHash lên 16 bắt thêm một ca calib, nhưng một ca tương đương 16,7 điểm phần trăm recall vì chỉ có sáu ca gần trùng. Hai cặp gần trùng trên raw (`img_0076`–`img_0042` và `img_0143`–`img_0037`) đều có khoảng cách 0. Ảnh chồng nhãn cho thấy lần lượt cùng xe buýt đêm và cùng cảnh đường phố, nên mức tăng recall trên calib không chứng minh lợi ích tương đương trên raw. Với cờ ngữ nghĩa, ngưỡng thấp ưu tiên đưa nghi vấn đến người duyệt và chấp nhận Hold khi vượt ngân sách.

## 4. Kiểm tra cửa chặn và điểm mù

Lệnh `python -m pipeline.run --budget 0 --work work/run_nb --reports work/rep_nb --export-dir work/exp_nb` trả **20 (Rework)** với 6 lỗi thiếu file nhãn. Kiểm tra thấy `exported: null` và không có `work/exp_nb/clean_v1`. Vòng chuẩn chạy với ngân sách 80 và cổng giữ nguyên 10%.

- Đã xem 12 ảnh chồng nhãn raw. `img_0030` dòng 9 và `img_0043` dòng 1 tràn biên, còn `img_0031` có xe buýt hiện rõ nhưng thiếu file nhãn. Cắt biên sửa được hình học, độ sát vật vẫn cần xem lại.
- **Gần trùng biến đổi mạnh.** Sweep ở ngưỡng 4 bỏ sót 2/6 cặp đã chèn. Phép đo pHash toàn ảnh dễ đổi khi cắt lại khung. Người duyệt có thể dùng đối chiếu vùng trên các cặp nghi vấn trước khi loại.
- **Đồng thuận sai và vật nhỏ.** Ý kiến thứ hai chỉ cảnh báo khi hai nguồn có dấu hiệu bất đồng. Ví dụ `img_0160` có nhiều xe ở xa, nhãn raw chỉ phủ một phần. Dự đoán dưới 600 px² không tạo cờ thiếu, và xe cả hai model cùng bỏ sót cũng không thể tạo cờ. Lấy mẫu ảnh đông đối tượng, kể cả ảnh ít cờ, để kiểm thủ công.

## 5. Train raw và clean

Chưa có kết quả hoàn chỉnh. Lượt thử MPS cục bộ dừng vì tốc độ thấp. Đã khởi chạy lại bằng Tesla T4 trên Colab với `scripts/train_compare.py`, YOLO26n, 20 epoch, seed 0 và 1, ảnh 640 px và batch 16 cho cả hai biến thể. Cùng 40 ảnh val để chọn checkpoint và 100 ảnh test để đo cuối.

## 6. Quyết định và ghi chú AI

Giữ **Hold**. Với 205 ảnh, điều kiện để Release là 0 lỗi bắt buộc và tối đa 20 ảnh có cảnh báo chưa duyệt. Cần xử lý thêm ít nhất 44 trong 64 ảnh đang có cờ nếu mẫu số và tập cờ còn lại giữ nguyên. Ưu tiên khác lớp, thiếu vật và cảnh dày đối tượng. Chạy QC vòng cuối sau đợt duyệt bổ sung đã được phê duyệt.

- **Prompt chính dùng với Codex:** đọc docstring và test của bốn module. Nhận YOLO `id cx cy w h` chuẩn hoá và dự đoán kèm confidence, đối chiếu hình học theo YAML và sinh `Issue` có mã, ảnh, dòng. Sửa trên bản sao, ghi trước/sau, chuyển lỗi ngữ nghĩa sang người, trả phán quyết có số liệu. Giữ nguyên dữ liệu, test và các file được ghim.
- **Kiểm tra với Codex:** 79 test gốc, hai sweep trên lỗi chèn, bộ ca tổng hợp gồm dòng trống, lỗi kép, nhiều dự đoán, và chạy pipeline đủ ngân sách lẫn ngân sách 0. Codex hỗ trợ viết code và báo cáo. Người nộp cần đọc và giải thích được code theo quy định lab.
- **Điểm AI phải sửa:** thử nghiệm cho thấy chỉ bắt `ValueError` như mô tả của parser sẽ làm ID lớp `inf` dừng check bằng `OverflowError`. Hai check xử lý cả hai ngoại lệ. Ca thử xác nhận dòng hỏng được ghi đúng số và các dòng khác vẫn được kiểm.

**Kiểm bổ sung.** `python -m pipeline.checks.box_aspect --dataset work/run/ds --max-ratio 8 --out submission/evidence/box_aspect.csv` đo tỉ lệ cạnh theo pixel. Có [2 cờ trên 205 ảnh](evidence/box_aspect.csv): `img_0042` dòng 5 (9,58:1) và `img_0124` dòng 6 (9,11:1). Kiểm này chạy độc lập và chỉ cảnh báo để người duyệt phân biệt vật thật dài/mỏng với box lỗi. Bốn ca test bổ sung kiểm đơn vị pixel, ngưỡng đúng bằng giới hạn, dòng hỏng và tham số không hợp lệ.
