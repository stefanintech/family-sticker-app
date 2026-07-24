# Family Sticker Machine — Project Handoff

Context summary for picking this project up in a different LLM/tool. No secrets
included — see "Secrets" section at the bottom for what you still need to supply.

## What this is

A local app for a family: type or say a sticker idea, get an AI-generated
black-and-white coloring-page image, preview it, and print it as a 4x6 adhesive
label on a Phomemo PM-241BT thermal printer plugged into a Mac via USB.

Repo: https://github.com/stefanintech/family-sticker-app

## Stack & architecture

- Single Python/Flask app (`app.py`), one HTML page (`templates/index.html`),
  vanilla JS — no frontend framework, no build step, no database.
- Image generation + voice transcription: Google's Gemini API (`google-genai`
  SDK), using an API key stored in `.env` (gitignored).
  - Image model: `gemini-2.5-flash-image`
  - Transcription model: `gemini-flash-latest` (had to switch off
    `gemini-2.5-flash` mid-project — Google deprecated it for new-user access)
- Printing: `printer.py` shells out directly to CUPS (`lp -d PM-241-BT ...`) —
  no browser print dialog involved. The PM-241BT already had a working CUPS
  driver installed on this Mac (queue name `PM-241-BT`, PPD-based, 203dpi,
  default media `w288h432` = exactly 4x6in), which simplified this a lot —
  no raw USB/libusb protocol work was needed.
- Server runs over **self-signed HTTPS**, bound to the LAN (`0.0.0.0`), because
  browser microphone access (`getUserMedia`) requires a secure context — plain
  HTTP from a phone would silently fail to even prompt for mic permission.

## Files

```
app.py              Flask routes: /, /generate, /voice, /print
printer.py          Image post-processing (B&W threshold + margin) + CUPS print
templates/index.html Single-page UI: text input, hold-to-talk button, preview, print
requirements.txt    flask, python-dotenv, google-genai, pillow, pyopenssl
.env                GOOGLE_API_KEY (gitignored, NOT in repo)
generated/          Saved output PNGs (gitignored, NOT in repo)
PLAN.md             Original architecture/phasing plan, written before any code
README.md           Setup + run instructions
```

## What's built and working (verified on real hardware, not just tests)

1. **Text input → generate → preview → print.** Confirmed producing consistent
   clean coloring-book-style line art (bold outlines, no shading/color).
2. **Direct thermal printing.** Bypasses the browser entirely via CUPS. Fixed one
   real issue along the way: the first prints had sun-ray tips clipped at the
   label edges — fixed by padding the artwork with an ~8% white margin before
   sending it to the printer (`MARGIN_RATIO` in `printer.py`).
3. **Voice control ("hold to talk").** Press-and-hold records via
   `MediaRecorder`, release uploads audio to `/voice`, which transcribes via
   Gemini and feeds the text into the same image pipeline, then auto-prints
   after a ~1.5s flash preview. Verified end-to-end from an actual iPhone over
   the LAN, including real prints.
4. **Visual redesign.** Kid-friendly styling pass: Fredoka rounded font (Google
   Fonts), warm pastel gradient background, big colorful hold-to-talk button as
   the primary visual action, typing tucked behind a collapsible "or type an
   idea instead", card-style preview with a placeholder state.
5. **Error handling.** Empty input, Gemini API failures, and CUPS print
   failures all surface as readable in-page messages instead of crashing.

## Notable gotchas hit and resolved

- **Free-tier quota was 0 for image generation.** Google requires billing
  enabled on the project behind the API key, even for light/occasional use.
  Swapping API keys within the same Google account didn't help — the fix was
  enabling billing on the linked Cloud project.
- **`gemini-2.5-flash` got deprecated for new users mid-project** — swapped the
  voice-transcription model to `gemini-flash-latest` (a stable alias, avoids
  hardcoding version numbers that go stale again).
- **Pillow was missing from `requirements.txt`** the first time `printer.py`
  was added — crashed Flask's autoreloader. Fixed by adding it.
- **Headless-Chrome screenshot testing produced a false-positive layout bug**
  (content looked clipped at narrow widths). Proved via a trivial test page
  that it was a Chrome `--screenshot` rendering quirk, not a real CSS bug — the
  actual page was fine, confirmed via a wide-viewport render and, ultimately,
  a real phone.
- **Named copyrighted characters won't generate as their real likeness** (e.g.
  asked for "Huntrix" characters from *KPop Demon Hunters* — got generic
  original-style stand-ins instead, captioned with the show's name). This is a
  built-in IP guardrail on Google's image model, not something fixable via our
  own prompt template. Workaround: describe the character's visual attributes
  (hairstyle, outfit, colors, vibe) instead of naming the franchise/character.

## Explicitly out of scope (by design, not oversight)

No auth, no database/history gallery, no multiple label sizes, no color
printing, no Raspberry Pi support, no Bluetooth printing (USB only). See
`PLAN.md` for the full original scoping rationale.

## Possible next steps (not started)

- Loading spinner/nicer disabled states beyond plain status text.
- A small in-memory gallery of the last few generated images (still no DB) so a
  mis-tap on Regenerate doesn't lose the previous result before printing.
- PPD-level print tuning (`Darkness`, `AdjustHorizontal/Vertical`) if future
  labels come out mis-aligned or too light/dark — options already discovered
  and documented in `PLAN.md` §4, just not yet needed.

## Secrets — not included here, you'll need to supply your own

- `GOOGLE_API_KEY` in a local `.env` file — a Gemini API key from
  [Google AI Studio](https://aistudio.google.com/apikey), on a project with
  billing enabled (image generation is unavailable on the free tier).
- Note: an earlier API key was pasted in plaintext during this project's chat
  history. It was never committed to the repo, but if you're the same user
  continuing this project, consider rotating it in Google AI Studio since it
  passed through chat text at least once.
