# Family Sticker Machine — Plan

Inspired by [wesbos/sticker-dream](https://github.com/wesbos/sticker-dream). A local
app where a kid/parent types an idea, gets a black-and-white coloring-page image,
previews it, and prints it as a 4x6 label on a Phomemo PM-241BT over USB.

No implementation yet — this document captures architecture, scope, risks, and the
build order.

## 1. Recommended architecture

**Single small Python (Flask) app, one process, no build step.**

- Backend: Flask serves one HTML page and two JSON endpoints:
  - `POST /generate` — takes the typed idea, calls an image-generation API with a
    fixed "coloring page" prompt template, saves the PNG to disk, returns its path/URL.
  - `POST /print` — takes the last generated image, post-processes it (resize/pad to
    label dimensions, force pure black/white), and sends it to the Phomemo printer.
- Frontend: one plain HTML page, vanilla JS (`fetch`), no framework, no bundler.
  Text input → Generate button → `<img>` preview → Print button → status line.
- Image generation: an external text-to-image API (e.g. OpenAI's image API), called
  with `requests`. No local ML model — keeps dependencies minimal and avoids GPU/setup
  concerns on a MacBook.
- Image post-processing: Pillow — threshold to pure black/white, resize/pad to the
  label's pixel dimensions, dither if the printer needs true 1-bit bitmaps.
- Printing: a small printer module that talks to the PM-241BT over USB. Exact
  approach (CUPS raw queue vs. raw USB bytes) is **unknown until Phase 0** — see
  risks below.

Why Python over Node: Pillow is the simplest path to reliable image post-processing,
and most existing community reverse-engineering of Phomemo printers is in Python —
better odds of reusable reference code for the printer piece.

## 2. Minimum files

```
app.py              # Flask routes: /, /generate, /print
templates/index.html  # single-page UI (input, preview, buttons, status)
printer.py           # isolated printer module (USB send, tested standalone first)
generate.py          # isolated image-gen module (prompt template, API call, save PNG)
requirements.txt     # flask, requests, pillow, python-dotenv (+ printer lib once known)
.env                 # image-gen API key (gitignored)
generated/           # output PNGs (gitignored)
```

That's it — 4 code files. `generate.py` and `printer.py` are split out specifically
so each can be run and tested from the command line without the web app.

## 3. MVP scope

**In scope:**
- One text input, one fixed "coloring page" style (no style picker).
- Generate → preview → Print, sequentially, one image at a time.
- Printer target is hardcoded (one printer, no device picker).
- Files kept on disk; "current image" tracked as just the latest file — no database.

**Explicitly out of scope for v1:**
- Accounts, history/gallery of past stickers, multiple paper sizes, color printing,
  cropping/editing UI, print queue for multiple images, mobile app, packaging as a
  standalone Mac app.

## 4. Printer setup risks on macOS (resolved better than expected)

**Update (confirmed on this machine, 2026-07-23):** a Phomemo driver is already
installed and the printer is already a working CUPS queue:

- `lpstat -p` shows `PM-241-BT`, idle, connected via `usb:///PM-241-BT?serial=...`.
- PPD is real (`/private/etc/cups/ppd/PM-241-BT.ppd`, driver v1.4.3), using CUPS
  filter `rastertolabeltspl` — TSPL is a standard label-printer command language,
  so CUPS handles the raw protocol translation for us.
- Resolution: `203dpi`. Default page size `w288h432` (PostScript points) = **exactly
  4in × 6in** — matches the label stock with no custom size math needed.
- `ColorOption` supports `GrayScale` — the driver can dither, though we'll likely
  still pre-threshold/dither ourselves for a cleaner coloring-page look.
- Other tunable PPD options exist for offset/darkness/gap-tracking if alignment
  needs adjustment (`AdjustHorizontal`, `AdjustVertical`, `Darkness`, `GapHeight`,
  etc.).

**Conclusion: no raw USB/libusb work needed.** `printer.py` can shell out to
standard CUPS printing (`lp -d PM-241-BT ...` or Python's `pycups`/`subprocess`)
instead of hand-rolling a USB protocol. This removes the project's single biggest
risk — Phase 0 is now mostly "send one real test print and check size/alignment/
darkness," not protocol reverse-engineering.

Remaining smaller risks:
- Confirm the driver expects a pre-dithered 1-bit image vs. raw grayscale/RGB (test
  both if the first print looks wrong).
- First test print may need `AdjustHorizontal`/`AdjustVertical`/`GapHeight` tuning
  for this specific roll of labels.
- Confirm `w288h432` is actually correct for the label stock in the printer right
  now (measure a physical label, or check the PPD's currently loaded default vs.
  other listed sizes like `w288h468`).

## 5. Testing generation separately from printing

- `generate.py` is runnable standalone from the CLI (`python generate.py "a
  dinosaur"` → writes a PNG to `generated/`). This lets prompt/quality iteration
  happen with zero dependency on the printer.
- `printer.py` is runnable standalone against **any** local PNG, not just
  app-generated ones (`python printer.py sample.png`). Use a hand-picked sample
  coloring image to validate the print pipeline before generation is even built.
- Because the two hard problems (image-gen prompt quality, and USB printer
  protocol) are fully decoupled, they can be de-risked independently — a printer
  problem never blocks generation work and vice versa.
- The Flask app only wires these two already-proven pieces together; it shouldn't
  need its own debugging of either subsystem.

## 6. Phased implementation plan

**Phase 0 — Printer spike (do this first, it's the biggest unknown)**
Get *any* image to print successfully from a Mac to the PM-241BT over USB via a
throwaway script. Confirm: connection method (raw USB vs CUPS), required image
format/dimensions/DPI, and basic alignment. Don't write app code until this works.

**Phase 1 — Image generation core**
Pick the image-gen API, write the coloring-page prompt template, build `generate.py`
as a CLI script, iterate on prompt wording until output quality is consistently good
line art (thick outlines, no shading/color, white background).

**Phase 2 — Minimal web UI**
Build `app.py` + `templates/index.html`: text input, Generate button calling Phase
1's logic, image preview. No printing yet.

**Phase 3 — Print integration**
Wire the Print button to Phase 0's printer script, running the generated image
through the post-processing step (resize/pad/threshold/dither) first.

**Phase 4 — Polish**
Loading/error states for both API failures and printer failures, basic CSS, maybe a
"Regenerate" button. Stop here for v1.

## 7. Open decisions before starting

- ~~Which image-generation API/key to use~~ — **resolved**: Google API key provided,
  stored in `.env` (gitignored). Use Google's image generation (Gemini/Imagen) via
  the Gemini API. Need to confirm exact model name/endpoint (e.g. `imagen-3.0` or a
  Gemini image-preview model) and check quota/pricing for the key provided.
- ~~Whether the PM-241BT is reachable on this Mac~~ — **resolved**: yes, already
  installed as CUPS queue `PM-241-BT` over USB, driver v1.4.3, default media
  4x6in @ 203dpi. See §4.
- Both blockers for Phase 0/1 are now cleared — next step is a real test print (uses
  a physical label) and a first Gemini image-gen call, to validate both pipelines
  end to end before wiring the web app together.
