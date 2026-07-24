# Family Sticker Machine

Say or type a sticker idea, get a black-and-white coloring-page image, preview it,
and print it straight to a Phomemo PM-241BT 4x6 thermal label printer.

Two ways to use it:
- **Type an idea** → Generate → Regenerate/Print.
- **Hold the talk button, describe it, let go** → it transcribes, generates, shows a
  quick preview, and prints automatically.

See `PLAN.md` for the original design plan and phased build order.

## How it works

- Single Flask app (`app.py`) serving one page (`templates/index.html`) with no
  frontend framework or build step.
- Image generation and voice transcription both go through the Gemini API
  (`google-genai`), using a fixed coloring-book prompt template.
- Printing goes straight to CUPS (`lp -d PM-241-BT ...`) via `printer.py` — no
  browser print dialog involved. The image is thresholded to pure black-and-white
  and padded with a small margin before printing, so it prints cleanly and doesn't
  clip at the label's edges.
- The server runs over HTTPS with a self-signed cert and binds to your LAN, because
  microphone access requires a secure context — this is required for the
  hold-to-talk feature to work from a phone.

## Requirements

- Python 3.10+
- A Phomemo PM-241BT already set up as a macOS printer (see below) named
  `PM-241-BT` in CUPS — check with `lpstat -p`.
- A Google API key with a **billing-enabled** project (image generation is not
  available on the free tier — see [ai.google.dev](https://ai.google.dev/gemini-api/docs/rate-limits)).

## Setup

1. Create and activate a virtual environment:

   ```
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Add your Google API key. Create a `.env` file in the project root (gitignored,
   never commit this) with:

   ```
   GOOGLE_API_KEY=your-key-here
   ```

   Get a key from [Google AI Studio](https://aistudio.google.com/apikey), and make
   sure billing is enabled on the associated Google Cloud project.

## Printer setup (macOS)

The PM-241BT needs to already be installed as a CUPS printer named `PM-241-BT`
before this app can print to it — install Phomemo's macOS driver first, connect
the printer over USB, then confirm it shows up:

```
lpstat -p PM-241-BT
```

If that reports the printer as idle, you're set. `printer.py` assumes a 4x6in
label (`w288h432`) and will need its `MEDIA_SIZE`/`PRINTER_NAME` constants updated
if your setup differs.

## Run

```
source .venv/bin/activate
python app.py
```

This starts an HTTPS server on port 5001, bound to all interfaces. On startup it
prints both URLs:

- `https://127.0.0.1:5001` — for use on the Mac itself.
- `https://<your-lan-ip>:5001` — for use from a phone on the same Wi-Fi (required
  for the hold-to-talk feature).

Since the HTTPS cert is self-signed, your browser will warn it's untrusted the
first time — accept/proceed through that warning. It regenerates on every server
restart, so this happens again each time you restart the app.

## Use

**Typing:**
1. Tap "or type an idea instead" and enter a sticker idea (e.g. "a happy sun").
2. Tap **Generate**. The coloring-page image appears below.
3. Tap **Regenerate** to try again, or **Print** to send it straight to the printer.

**Voice:**
1. Allow microphone access when prompted.
2. Hold the "Hold to Talk" button, say what you want, then let go.
3. It transcribes, generates, shows the image briefly, then prints automatically.

Generated images are also saved to `generated/` (gitignored) for reference.

## Known limitations

- Named copyrighted/trademarked characters (movie characters, franchise mascots,
  etc.) won't generate as their real likeness — the model substitutes a generic,
  original-style character instead. This is a built-in guardrail on Google's
  image model, not something this app's prompt controls. Describing a character's
  visual look (hairstyle, outfit, colors, vibe) instead of naming the franchise
  gets much closer results.
- No auth, no history/gallery, no multiple sizes or color printing — see
  `PLAN.md` for intentional MVP scope.

## If I had more time, I'd want to...

**Make it friendlier for kids day-to-day**
- Add a difficulty/complexity control (toddler vs. big-kid) so the artwork's fill
  areas scale to the child's age instead of one fixed style for everyone.
- Show a live waveform or "listening" animation while recording, instead of static
  status text — makes the mic actually feel like it's paying attention.
- Let a kid see the transcribed text for a beat before it prints, in case the mic
  mishears — right now a bad transcription just prints anyway.

**Reduce the friction of running it**
- Swap the ad-hoc self-signed cert for a locally-trusted one (e.g. via `mkcert`),
  so the phone doesn't need to click through a certificate warning every single
  time the server restarts.
- Turn the page into an installable PWA with a home-screen icon, so it's a normal
  app tap instead of typing an HTTPS LAN address from memory.
- Auto-detect the printer's actual media size/DPI from the PPD instead of hardcoding
  `w288h432` in `printer.py`, so it isn't tied to this one specific label roll.

**Round out reliability**
- Poll the actual CUPS job status after printing instead of trusting `lp`'s exit
  code — right now a jam or empty label roll wouldn't necessarily surface as an
  error in the UI.
- A tiny in-memory gallery of the last few generated stickers, so a mis-tap on
  Regenerate doesn't lose the previous result before it's been printed.
- Basic automated tests around the image post-processing (threshold/margin math in
  `printer.py`) and the prompt template — currently everything was verified by
  hand against real hardware, which was the right call for a fast build, but
  wouldn't scale if the project grew.

**Fun stretch ideas**
- Multi-language voice support (Gemini can already transcribe non-English audio) —
  nice for bilingual households.
- A small running counter of labels used, since a roll is a finite, physical
  resource a parent might want to keep an eye on.
