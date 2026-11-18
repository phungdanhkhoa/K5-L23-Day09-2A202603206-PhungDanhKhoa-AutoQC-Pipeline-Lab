"""CHECK 2 — Dòng nhãn YOLO: sai định dạng, ID lớp lạ, box tràn ảnh, box rỗng, box lặp.   (Script 2 trong slide)   ★★

Test:  pytest tests/test_label_format.py -q

Mỗi dòng nhãn: `id cx cy w h` (5 số, toạ độ 0–1). Trả về list[Issue]; `Issue.line` = số dòng (đếm từ 1).

| code             | severity | khi nào                                                                  |
|------------------|----------|--------------------------------------------------------------------------|
| BAD_FORMAT       | ERROR    | không đúng 5 cột số (dùng `parse_yolo_line`, bắt `ValueError`)           |
| BAD_CLASS_ID     | ERROR    | id lớp ngoài 0..len(ds.classes)-1                                        |
| BOX_ZERO         | ERROR    | w <= 0 hoặc h <= 0                                                       |
| BOX_OUT_OF_IMAGE | ERROR    | mép box vượt [0,1] quá `cfg["label_format"]["overflow_tol"]`; extra={"overflow": mức tràn} |
| DUP_BOX          | ERROR    | cùng lớp với một dòng TRƯỚC ĐÓ và IoU > `dup_box_iou`; báo ở dòng SAU    |
| BOX_TINY         | WARN     | cạnh ngắn của box (px) < `min_box_px`  (cần `ds.image_size(stem)`)       |
| BOX_HUGE         | WARN     | w*h > `max_box_frac`                                                     |

Gợi ý
- Mép trái = x - w/2, mép phải = x + w/2 (xem câu hỏi "dòng YOLO nào lỗi?" trong slide).
- Một dòng hỏng (BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO) thì `continue`, đừng kiểm tiếp hình học của dòng đó.
- Dòng thiếu cột làm script của slide dừng giữa chừng: đây là lý do phải `try/except`.
- `iou_xywh(a, b)` có sẵn trong common.py.
- Ngưỡng nằm trong `cfg["label_format"]` — đừng viết cứng số vào code.
"""
from collections import defaultdict

from ..common import ERROR, WARN, Issue, iou_xywh, parse_yolo_line


def run(ds, cfg):
    settings = cfg["label_format"]
    issues = []
    for path in ds.label_files():
        stem = path.stem
        size = ds.image_size(stem)
        previous_by_class = defaultdict(list)
        for number, raw in ds.read_label_lines(stem) or []:
            try:
                cls, cx, cy, w, h = parse_yolo_line(raw)
            except (ValueError, OverflowError) as exc:
                issues.append(Issue("label_format", ERROR, "BAD_FORMAT", stem, str(exc), number))
                continue
            if not 0 <= cls < len(ds.classes):
                issues.append(Issue("label_format", ERROR, "BAD_CLASS_ID", stem, f"ID lớp ngoài danh sách: {cls}", number))
                continue
            if w <= 0 or h <= 0:
                issues.append(Issue("label_format", ERROR, "BOX_ZERO", stem, f"kích thước không dương: {w:g} × {h:g}", number))
                continue

            box = (cx, cy, w, h)
            overflow = max(0.0, w / 2 - cx, h / 2 - cy, cx + w / 2 - 1, cy + h / 2 - 1)
            if overflow > settings["overflow_tol"]:
                issues.append(Issue("label_format", ERROR, "BOX_OUT_OF_IMAGE", stem, f"box tràn {overflow:.4g} theo tỉ lệ ảnh",
                                    number, {"overflow": overflow}))
            earlier = previous_by_class[cls]
            if any(iou_xywh(box, old) > settings["dup_box_iou"] for old in earlier):
                issues.append(Issue("label_format", ERROR, "DUP_BOX", stem, "box chồng mạnh với dòng trước cùng lớp", number))
            earlier.append(box)

            if size:
                short_px = min(w * size[0], h * size[1])
                if short_px < settings["min_box_px"]:
                    issues.append(Issue("label_format", WARN, "BOX_TINY", stem, f"cạnh ngắn {short_px:.2f}px", number))
            area = w * h
            if area > settings["max_box_frac"]:
                issues.append(Issue("label_format", WARN, "BOX_HUGE", stem, f"diện tích bằng {area:.1%} ảnh", number))
    return issues
