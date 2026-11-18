import pytest
from PIL import Image

from pipeline.checks import box_aspect
from pipeline.common import WARN, Dataset


def test_aspect_uses_pixels_and_preserves_source_line(tmp_path):
    ds = Dataset(tmp_path, ["car"])
    ds.images_dir.mkdir()
    ds.labels_dir.mkdir()
    Image.new("RGB", (800, 400)).save(ds.images_dir / "road.JPG")
    labels = ds.label_path("road")
    labels.write_text(
        "0 .5 .5 .4 .1\n"        # 320 × 40, exactly 8:1
        "\n"
        "0 .5 .5 .5 .1\n"        # 400 × 40, 10:1
        "0 .5 .5 .025 .5\n"      # 20 × 200, 10:1
        "0 .5 .5 0 .2\n"
        "inf .5 .5 .5 .1\n"
        "garbage\n"
    )
    before = labels.read_bytes()
    issues = box_aspect.run(ds, max_ratio=8)
    assert [(i.image, i.line, i.severity, i.code) for i in issues] == [
        ("road", 3, WARN, "BOX_ASPECT_EXTREME"),
        ("road", 4, WARN, "BOX_ASPECT_EXTREME"),
    ]
    assert box_aspect.run(ds, max_ratio=10) == []
    assert labels.read_bytes() == before


@pytest.mark.parametrize("ratio", [0.9, float("inf"), float("nan")])
def test_invalid_ratio_is_rejected(tmp_path, ratio):
    with pytest.raises(ValueError):
        box_aspect.run(Dataset(tmp_path, ["car"]), max_ratio=ratio)
