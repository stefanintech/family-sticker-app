import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image

PRINTER_NAME = "PM-241-BT"
MEDIA_SIZE = "w288h432"  # 4in x 6in, matches the PM-241BT's default label size


MARGIN_RATIO = 0.08  # white border added around the artwork so edges aren't clipped


def prepare_for_print(image_bytes: bytes) -> bytes:
    """Convert an image to pure black-and-white with a safety margin, suited to a
    thermal label printer whose physical edge/alignment isn't pixel-precise."""
    img = Image.open(BytesIO(image_bytes)).convert("L")
    bw = img.point(lambda x: 0 if x < 128 else 255, mode="1")

    w, h = bw.size
    margin_w = int(w * MARGIN_RATIO)
    margin_h = int(h * MARGIN_RATIO)
    padded = Image.new("1", (w + margin_w * 2, h + margin_h * 2), 255)
    padded.paste(bw, (margin_w, margin_h))

    out = BytesIO()
    padded.save(out, format="PNG")
    return out.getvalue()


def print_image(image_bytes: bytes) -> None:
    """Send an image straight to the Phomemo PM-241BT via CUPS. Raises on failure."""
    processed = prepare_for_print(image_bytes)
    tmp_path = Path("/tmp/sticker_print.png")
    tmp_path.write_bytes(processed)

    result = subprocess.run(
        [
            "lp",
            "-d", PRINTER_NAME,
            "-o", f"media={MEDIA_SIZE}",
            "-o", "fit-to-page",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "lp command failed")
