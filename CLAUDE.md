# apify-actor-assets — CLAUDE.md

> Global rules (owner profile, workflow, external AI, git push discipline) → `~/.claude/CLAUDE.md`.
> Current state → `summary.md`. Open tasks → `Task_List.md`. Never log mutable state here.

## What this repo is

Public image hosting for [Apify Store](https://apify.com/store) actor pages. Apify has no
screenshot gallery, so every visual on an actor page is a markdown image served from
`raw.githubusercontent.com` out of this repo. **Images and nothing else** — no source code,
no credentials, no notes; the actors live in a private repository. Layout and URL scheme:
`README.md`.

## Rules

- Chat with the owner in Ukrainian; files, commits and docs in English.
- **This repo is public.** Anything committed is world-readable the moment it lands —
  never add credentials, tokens, real customer data, or non-image files beyond the
  README/contract set. `src/` captures of real product UI are allowed (README documents why).
- Push discipline: `git add` only named files, never `-A`; the push-safety gate
  (`scripts/check-push-safety.py` via the PreToolUse hook) must pass — never bypass it.
- Served image URLs are referenced from live Store pages: **renaming or deleting a served
  PNG breaks the actor's public page** — check the actor README before touching one.
- Checkpoints: `summary.md` and `Task_List.md` each ≤80 lines AND ≤8000 bytes (the
  SessionStart hook cuts at the first cap hit and prints `[TRUNCATED …]`).
