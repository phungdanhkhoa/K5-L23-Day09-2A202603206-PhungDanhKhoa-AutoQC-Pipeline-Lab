"""BƯỚC 4 — Cửa chặn: quyết định Release / Hold / Rework.   ★

Test:  pytest tests/test_gate.py -q

Cây quyết định Day 07 (slide Day 09: "Lỗi bắt buộc chặn pipeline; lỗi cảnh báo chuyển người xem"):

  còn ≥ 1 lỗi bắt buộc (severity ERROR)                          -> "Rework"
  không còn lỗi bắt buộc, nhưng tỉ lệ ẢNH còn cảnh báo
      >= cfg["gate"]["warn_ratio_hold"]                          -> "Hold"
  còn lại                                                        -> "Release"

Tỉ lệ cảnh báo = (số ẢNH khác nhau có ≥ 1 cảnh báo) / (tổng số ảnh).  Chú ý:
- chỉ đếm issue có `image` nằm trong `image_stems` (bỏ "<dataset>", "data.yaml");
- bỏ qua ảnh nằm trong `reviewed` (người đã xem, cảnh báo của ảnh đó coi như đã xử lý) — nhưng LỖI BẮT BUỘC thì không bao giờ được bỏ qua;
- mẫu số là số ảnh, không phải số issue.

Trả về dict: decision, n_errors, n_warn_images, n_images, warn_ratio (làm tròn 4 chữ số), reasons (list[str], giải thích bằng tiếng Việt, có số liệu).
"""
from ..common import ERROR, WARN


def decide(issues, image_stems, cfg, reviewed=frozenset()):
    stems = set(image_stems)
    pending = stems.difference(reviewed)
    errors = 0
    warned = set()
    for issue in issues:
        if issue.severity == ERROR:
            errors += 1
        elif issue.severity == WARN and issue.image in pending:
            warned.add(issue.image)

    count = len(stems)
    ratio = len(warned) / count if count else 0.0
    limit = cfg["gate"]["warn_ratio_hold"]
    if errors:
        decision = "Rework"
        reasons = [f"còn {errors} lỗi bắt buộc"]
    else:
        decision = "Hold" if ratio >= limit else "Release"
        relation = "≥" if ratio >= limit else "<"
        reasons = ["0 lỗi bắt buộc", f"{len(warned)}/{count} ảnh còn cảnh báo chưa duyệt ({ratio:.2%} {relation} {limit:.0%})"]
    return dict(decision=decision, n_errors=errors, n_warn_images=len(warned), n_images=count,
                warn_ratio=round(ratio, 4), reasons=reasons)
