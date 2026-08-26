---
worth: later
added: 2026-08-20
---
# Nobody checked that the live Store page actually uses all 4 served images

- **Where**: the 4 images served from this repo; the referencing README lives in the private
  actors repo, not here
- **Why deferred**: it was not verifiable during onboarding — the README is in another repo and
  the check needs the live Store page
- **Consequence**: either an image is dead weight served for nothing, or the Store page points at
  a file this repo does not serve — a broken image on a public listing that sells the actor
- **Action**: open the actor's Store page, diff the filenames it references against the 4 served
  here, and drop or add accordingly
- **Logged**: 2026-08-20 (migrated from `summary.md` § Known gaps)
