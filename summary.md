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

- Whether all 4 served images are actually referenced by the live Store README was not
  verified during onboarding (the actor's README lives in the private actors repo).

## Next steps

- None scheduled — repo is passive; it changes only when an actor's Store page images
  change.
