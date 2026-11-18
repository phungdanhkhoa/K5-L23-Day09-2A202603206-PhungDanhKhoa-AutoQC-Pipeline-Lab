"""BƯỚC 2/4 — Sửa tự động những lỗi bắt buộc mà máy sửa được AN TOÀN.   ★★

Test:  pytest tests/test_autofix.py -q

`fix(ds, issues, cfg) -> list[dict]`: duyệt `issues` (chỉ lỗi severity ERROR), sửa thẳng vào thư mục `ds`,
và trả về danh sách thay đổi; mỗi phần tử có khoá: image, line, action, before, after
(đây chính là file `03_fixes.csv` — bằng chứng pipeline đã làm gì, người có thể kiểm lại).

| code lỗi                                       | cách sửa                                    | action           |
|------------------------------------------------|---------------------------------------------|------------------|
| BAD_FORMAT, BAD_CLASS_ID, BOX_ZERO, DUP_BOX    | xoá dòng đó khỏi file nhãn                  | "drop_line"      |
| BOX_OUT_OF_IMAGE                               | cắt box về trong [0,1] (giữ nguyên lớp)     | "clip_box"       |
| MISSING_LABEL_FILE                             | KHÔNG sửa file (máy không thể bịa nhãn): ghi 1 dòng fix, before="(không có file)", after="chuyển người gán" | "needs_label" |
| BAD_CLASS_NAME                                 | ghi lại `names` trong data.yaml đúng `cfg["classes"]` | "rename_classes" |
| DUP_IMAGE_*, LEAK_TEST, CORRUPT_IMAGE, BAD_SIZE| xoá ảnh + nhãn khỏi `ds`                    | "remove_image"   |

Bẫy cần nghĩ tới (có test cho từng cái)
- Một file có NHIỀU dòng lỗi: số dòng trong `issues` là số dòng GỐC. Nếu xoá từng dòng một thì số dòng lệch.
  Gom theo file, rồi ghi lại MỘT lần.
- Sau khi cắt, box có thể không còn diện tích (nằm hẳn ngoài ảnh): lúc đó xoá dòng thay vì ghi box rỗng.
- Một dòng có 2 lỗi (vd. BOX_OUT_OF_IMAGE + DUP_BOX): xoá dòng thắng, chỉ ghi 1 fix `drop_line`, không ghi thêm `clip_box`. Dòng trống ở giữa file vẫn đếm vào số dòng gốc.
- Ảnh vừa bị xoá (DUP_IMAGE_*...) mà còn issue dòng của chính nó: bỏ qua êm, không được báo lỗi/chết.
- Không động tới lỗi WARN (cảnh báo là việc của người). Không sửa file ở `data/raw/` — chỉ sửa `ds`.
- Chạy lần 2 trên dữ liệu đã sửa phải không làm gì thêm (idempotent) — NGOẠI LỆ duy nhất: `needs_label` được ghi lại mỗi lần còn lỗi `MISSING_LABEL_FILE` (vì ảnh vẫn chưa có nhãn).

- `needs_label` KHÔNG tạo file nhãn rỗng (rỗng = "ảnh nền", khác với "chưa gán"). `review_queue` sẽ đẩy ảnh này lên đầu hàng đợi cho người.

Gợi ý: `yaml.safe_load / safe_dump`.
"""
from collections import defaultdict

import yaml

from ..common import ERROR, ROOT, parse_yolo_line

DROP_CODES = {"BAD_FORMAT", "BAD_CLASS_ID", "BOX_ZERO", "DUP_BOX"}
REMOVE_CODES = {"LEAK_TEST", "CORRUPT_IMAGE", "BAD_SIZE"}


def _clipped_label(raw):
    cls, cx, cy, w, h = parse_yolo_line(raw)
    left, right = max(0, cx - w / 2), min(1, cx + w / 2)
    top, bottom = max(0, cy - h / 2), min(1, cy + h / 2)
    if left >= right or top >= bottom:
        return ""
    values = ((left + right) / 2, (top + bottom) / 2, right - left, bottom - top)
    return " ".join([str(cls), *(format(value, ".16g") for value in values)])


def fix(ds, issues, cfg):
    raw = (ROOT / "data/raw").resolve()
    if ds.root.resolve().is_relative_to(raw):
        raise ValueError("autofix chỉ chạy trên bản sao làm việc")

    errors = [issue for issue in issues if issue.severity == ERROR]
    removed = {i.image for i in errors if i.code in REMOVE_CODES or i.code.startswith("DUP_IMAGE_")}
    changes = []
    for image in ds.image_files():
        if image.stem in removed:
            image.unlink()
            ds.label_path(image.stem).unlink(missing_ok=True)
            changes.append(dict(image=image.stem, line="", action="remove_image", before=image.name, after=""))

    if any(i.code == "BAD_CLASS_NAME" for i in errors):
        path = ds.yaml_path
        data = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
        if data.get("names") != cfg["classes"]:
            before = data.get("names")
            data["names"] = list(cfg["classes"])
            path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
            changes.append(dict(image="data.yaml", line="", action="rename_classes", before=before, after=data["names"]))

    needs_label = {i.image for i in errors if i.code == "MISSING_LABEL_FILE"} - removed
    for stem in sorted(needs_label):
        if not ds.label_path(stem).exists():
            changes.append(dict(image=stem, line="", action="needs_label", before="(không có file)", after="chuyển người gán"))

    by_file = defaultdict(lambda: defaultdict(set))
    for issue in errors:
        if issue.image not in removed and issue.line is not None:
            by_file[issue.image][issue.line].add(issue.code)

    for stem, by_line in sorted(by_file.items()):
        path = ds.label_path(stem)
        if not path.is_file():
            continue
        kept = []
        changed = False
        for number, raw_line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            codes = by_line.get(number, set())
            if codes & DROP_CODES:
                after = ""
            elif "BOX_OUT_OF_IMAGE" in codes:
                after = _clipped_label(raw_line)
            else:
                kept.append(raw_line)
                continue
            if after:
                kept.append(after)
            if after != raw_line:
                changed = True
                changes.append(dict(image=stem, line=number, action="clip_box" if after else "drop_line",
                                    before=raw_line, after=after))
        if changed:
            path.write_text("".join(line + "\n" for line in kept), encoding="utf-8")
    return changes
