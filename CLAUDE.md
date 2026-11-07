# apify-actor-assets

## What this is
Public image hosting for [Apify Store](https://apify.com/store) actor pages. Apify has no
screenshot gallery, so every visual on an actor page is a markdown image served from
`raw.githubusercontent.com` out of this repo. Images only — no source code, credentials or
notes; the actors live in a private repository. Layout and URL scheme: `README.md`.

## Rules
- The repo is public: anything committed is world-readable the moment it lands. No credentials,
  tokens, real customer data, or files beyond the images and the README/contract set. `src/`
  captures of real product UI are allowed (README says why).
- Never rename or delete a served image: live Store pages load it by URL, so the actor's public
  page breaks. Check the actor README before touching one.
