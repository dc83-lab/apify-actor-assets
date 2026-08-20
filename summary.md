# summary.md — apify-actor-assets

Last updated: 2026-08-08

## Current state

- Public image host for Apify Store actor pages; served via
  `raw.githubusercontent.com/dc83-lab/apify-actor-assets/main/<actor>/<file>.png`.
- One actor directory: `clutch-b2b-intelligence/` — 4 served PNGs (how-it-works,
  input-form, output, ai-artifact) + 1 raw capture in `src/` (off-machine backup only,
  never served).
- 2026-08-08: onboarded into the portfolio contract — CLAUDE.md, push-safety gate
  (canonical guard + PreToolUse hook wrapper), checkpoint files. Until then this was
  the only repo outside the secret-gate contour.

## Known gaps

- Moved to `DEBT.md` 2026-08-20 (one open item: Store README references for the 4 images).

## Next steps

- None scheduled — repo is passive; it changes only when an actor's Store page images
  change.
