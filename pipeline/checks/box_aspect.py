"""Kiểm bổ sung: cảnh báo box quá dài hoặc quá mỏng theo kích thước pixel.

Chạy độc lập để giữ nguyên quy tắc của pipeline chính và cửa chặn.
"""
from __future__ import annotations

import argparse
import math

from ..common import WARN, Dataset, Issue, load_config, parse_yolo_line, write_issues_csv


def run(ds, max_ratio=8.0):
    if not math.isfinite(max_ratio) or max_ratio < 1:
        raise ValueError("tỉ lệ cạnh tối đa phải hữu hạn và ≥ 1")

    issues = []
    for image in ds.image_files():
        size = ds.image_size(image.stem)
        if size is None:
            continue
        for number, raw in ds.read_label_lines(image.stem) or []:
            try:
                cls, _, _, w, h = parse_yolo_line(raw)
            except (ValueError, OverflowError):
                continue
            w_px, h_px = w * size[0], h * size[1]
            short, long = sorted((w_px, h_px))
            if not 0 <= cls < len(ds.classes) or short <= 0 or not math.isfinite(long):
                continue
            ratio = long / short
            if ratio > max_ratio:
                issues.append(Issue("box_aspect", WARN, "BOX_ASPECT_EXTREME", image.stem,
                                    f"tỉ lệ cạnh {ratio:.2f}:1 vượt {max_ratio:g}:1", number,
                                    {"width_px": w_px, "height_px": h_px}))
    return issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, help="thư mục YOLO có images/ và labels/")
    parser.add_argument("--max-ratio", type=float, default=8.0)
    parser.add_argument("--out", required=True, help="đường dẫn CSV")
    args = parser.parse_args()
    ds = Dataset(args.dataset, load_config()["classes"])
    if not ds.image_files():
        parser.error("không có ảnh trong thư mục đã chọn")
    if not math.isfinite(args.max_ratio) or args.max_ratio < 1:
        parser.error("--max-ratio phải hữu hạn và ≥ 1")
    issues = run(ds, args.max_ratio)
    write_issues_csv(issues, args.out)
    print(f"{len(issues)} cảnh báo trên {len({i.image for i in issues})}/{len(ds.image_files())} ảnh")


if __name__ == "__main__":
    main()
