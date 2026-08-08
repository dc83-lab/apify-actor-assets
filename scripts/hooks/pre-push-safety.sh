#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash): block `git push` when the push-safety guard fails.
# Reads the hook JSON payload on stdin; non-push commands pass through untouched.
# Exit 2 blocks the tool call (stderr is fed back to Claude); exit 0 allows it.
# Hardened 2026-07-02 (owner decision): fail-CLOSED on an unparseable payload, and
# token-aware push matching instead of a bare substring match.
# 2026-08-08: canon moved to ~/.claude/templates/pre-push-safety.sh and the base ref
# now falls back to the git empty-tree object when origin/main is absent, so a fresh
# repo's first push still scans its whole history (backported from fin-translate).
set -euo pipefail

payload="$(cat)"

# Fail-CLOSED: an empty payload gives us no command to inspect (jq would
# silently emit nothing and exit 0), so block rather than pass unguarded.
if [ -z "$payload" ]; then
  echo "pre-push-safety: empty hook payload — blocking (fail-closed)" >&2
  exit 2
fi

if ! command -v jq >/dev/null 2>&1; then
  # jq is a workstation prerequisite (validate-configs.sh already requires it).
  # Without it we cannot parse the payload; warn and fall back to the CI guard.
  echo "pre-push-safety: jq not found — hook skipped, CI guard remains" >&2
  exit 0
fi

# Fail-CLOSED: if the payload does not parse, we cannot rule the command out
# as a push, so block instead of letting it through unguarded.
if ! command_text="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null)"; then
  echo "pre-push-safety: cannot parse hook payload — blocking (fail-closed)" >&2
  exit 2
fi

# Match a real `git … push` invocation: a `git` token at a command boundary,
# optional global options (-C <path>, -c <k=v>, --flag[=value]), then a `push`
# token. Catches `git -C /x push`, `git -c a=b push`, `cd x && git push`.
# Residual over-match on quoted text (e.g. echo "git push") is accepted: it
# only runs the guard, which passes on a clean branch — errs in the safe direction.
push_re='(^|[;&|`([:space:]])git([[:space:]]+(-C[[:space:]]+[^[:space:]]+|-c[[:space:]]+[^[:space:]]+|--[[:alnum:]-]+(=[^[:space:]]*)?))*[[:space:]]+push([^[:alnum:]_-]|$)'
if ! printf '%s\n' "$command_text" | grep -Eq "$push_re"; then
  exit 0
fi

repo_root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
guard="$repo_root/scripts/check-push-safety.py"

if [ ! -x "$guard" ]; then
  echo "pre-push-safety: guard not found at $guard — blocking push (fail-closed)" >&2
  exit 2
fi

# Base for the range scan: origin/main if it exists, else the git empty-tree
# object so a brand-new repo's first push still scans its entire history.
base_ref="$(cd "$repo_root" && git rev-parse --verify --quiet origin/main || true)"
if [ -z "$base_ref" ]; then
  base_ref="$(cd "$repo_root" && git hash-object -t tree /dev/null)"
fi

if ! (cd "$repo_root" && ./scripts/check-push-safety.py --base "$base_ref" --head HEAD >&2); then
  echo "pre-push-safety: push-safety guard failed — push blocked" >&2
  exit 2
fi

exit 0
