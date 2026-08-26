#!/usr/bin/env python3
"""Push safety guard (fail-closed) — portfolio canonical copy.

This file is the single source of truth for the push-safety secret gate. A
byte-identical copy lives at ``scripts/check-push-safety.py`` in every portfolio
repo, because CI checks out only its own repo and cannot reach ``~/.claude``.
``homelab-infra/scripts/validate-configs.sh`` hash-checks the repo copy against
this one, so the copies cannot drift silently.

Two checks run, and both are conservative and fail-closed — any match, any error
and any unreadable input aborts with exit 1:

1. Blocked paths - refuse changes that add or modify files that must never
   enter git (real secret/key material, host-only runtime data, runner
   credentials). Mirrors the secret/data rules in ``.gitignore`` as a
   defense-in-depth gate against force-added files.
2. Secret canary - scan added diff lines for private keys and high-confidence
   credential shapes (tokens, cloud keys, LLM provider keys, WireGuard private
   keys). Matched values are never printed, only the file and the pattern name.

Modes:
  --staged             inspect the staged index (local, pre-commit)
  --base B --head H    inspect EVERY commit in the range B..H individually
                       (CI, pre-push hooks)

Range mode scans each commit on its own, not just the two endpoints. A secret
added in one commit and removed in a later commit inside the same range is
invisible to an endpoint diff, but it is still pushed and still recoverable from
the remote's history forever - so it must block.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


class GuardError(RuntimeError):
    """The guard could not complete a full inspection. Always blocks."""


# Example/template files are allowed even when their name matches a blocked
# glob (checked first). Their contents are still scanned by the secret canary.
ALLOWED_PATH_GLOBS = (
    "*.env.example",
    "*.example",
)

# Files that must never be committed. Matched against the full repo-relative
# path and its basename.
BLOCKED_PATH_GLOBS = (
    ".env", "*.env", ".env.*", "*.env.*",              # real env files
    "*.key", "*.pem", "*.p12", "*.pfx",                # key material
    "id_rsa", "id_ed25519",                            # ssh private keys
    "rclone.conf", "rclone.conf.*",                    # rclone remotes
    ".runner", ".credentials", ".credentials_rsaparams",  # gh runner creds
)

# Host-only runtime data directories that must never be committed. Matched as
# an exact path segment. This is the portfolio-wide floor; repos that need more
# add them through the overlay below rather than by editing this file.
BLOCKED_DIR_PARTS = frozenset({"secrets"})

# Repo-specific additions. The guard itself must stay byte-identical in every
# repo, so the one thing that legitimately differs per repo - which directory
# names are host-only data - lives in an optional JSON file next to this script:
#
#   scripts/push-safety-extra.json
#   {"blocked_dir_parts": ["data", "logs"]}
#
# An overlay can only ADD blocked directories; it can never remove a default
# check or relax a secret pattern. A present-but-unreadable overlay blocks.
OVERLAY_NAME = "push-safety-extra.json"

# High-confidence secret content shapes. Kept specific so placeholders such as
# ${VAR} or <value> never match. This is the union of every shape any portfolio
# repo has needed: an extra pattern only ever adds protection, so there is no
# reason for a repo to carry a shorter list.
SECRET_CONTENT_PATTERNS = (
    ("private key block", re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----")),
    ("Telegram bot token", re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{35}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b")),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[0-9A-Za-z_]{22,}\b")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Tavily API key", re.compile(r"\btvly-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI project key", re.compile(r"\bsk-(?:proj|svcacct)-[A-Za-z0-9_-]{20,}\b")),
    ("OpenAI legacy key", re.compile(r"\bsk-[A-Za-z0-9]{48}\b")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("WireGuard private key", re.compile(r"(?:Private|Preshared)Key\s*=\s*[A-Za-z0-9+/]{43}=")),
)

# Shared `git log` options for range mode. `--format=` suppresses the commit
# header and message entirely, so a commit message line beginning with `+` can
# never be mistaken for an added diff line. `--diff-merges=first-parent` makes
# merge commits emit their own diff too, so content introduced directly in a
# merge ("evil merge") is still scanned - an endpoint diff used to cover that
# case and the per-commit walk must not lose it.
LOG_OPTIONS = ("--format=", "--no-color", "--diff-merges=first-parent")


def run(*args: str) -> str:
    try:
        result = subprocess.run(
            args, check=True, capture_output=True, text=True, errors="replace"
        )
    except OSError as exc:  # git missing / not executable
        raise GuardError(f"cannot run `{' '.join(args)}`: {exc}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or f"exit {exc.returncode}"
        raise GuardError(f"`{' '.join(args)}` failed: {detail}") from exc
    return result.stdout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Push safety guard (fail-closed).")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--staged", action="store_true", help="inspect the staged index")
    mode.add_argument("--base", help="range base commit (requires --head)")
    parser.add_argument("--head", help="range head commit")
    args = parser.parse_args()
    if args.base and not args.head:
        parser.error("--base requires --head")
    return args


def load_overlay_dir_parts() -> frozenset[str]:
    """Extra blocked directory segments for this repo, or an empty set.

    Fail-closed: an overlay that exists but cannot be read or does not have the
    expected shape aborts the guard instead of being silently ignored.
    """
    path = Path(__file__).resolve().parent / OVERLAY_NAME
    if not path.is_file():
        return frozenset()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GuardError(f"cannot read overlay {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardError(f"overlay {path}: top level must be a JSON object")
    extra = data.get("blocked_dir_parts", [])
    if not isinstance(extra, list) or not all(isinstance(part, str) for part in extra):
        raise GuardError(f"overlay {path}: 'blocked_dir_parts' must be a list of strings")
    return frozenset(extra)


def is_commit(rev: str) -> bool:
    try:
        proc = subprocess.run(
            ("git", "cat-file", "-e", f"{rev}^{{commit}}"),
            capture_output=True,
            text=True,
        )
    except OSError:
        # git itself is unusable; let the next run() call raise a clear error.
        return False
    return proc.returncode == 0


def range_revs(args: argparse.Namespace) -> list[str]:
    """Revision arguments selecting every commit to be pushed.

    ``--base`` is normally a commit. fin-translate's pre-push hook passes the
    git empty-tree object when a fresh repo has no ``origin/main`` yet; that is
    a tree, not a commit, and ``git log <tree>..<head>`` would fail. Any base
    that is not a commit therefore means "scan the whole history reachable from
    head" - more scanning, never less.
    """
    if is_commit(args.base):
        return [f"{args.base}..{args.head}"]
    return [args.head]


def count_commits(revs: list[str]) -> int:
    out = run("git", "rev-list", "--count", *revs)
    try:
        return int(out.strip())
    except ValueError as exc:
        raise GuardError(f"unparseable `git rev-list --count` output: {out!r}") from exc


def changed_files(args: argparse.Namespace) -> list[str]:
    """Added/modified/renamed-destination paths only, deduplicated.

    Pure deletions are skipped: removing a file can never introduce a secret or
    a blocked host-data path, and the guard must not fight legitimate cleanup
    (e.g. deleting a previously-leaked ``.env``). In range mode a path added in
    one commit and deleted in a later one still appears here, via the commit
    that added it.
    """
    if args.staged:
        out = run("git", "diff", "--cached", "--name-status")
    else:
        out = run("git", "log", *LOG_OPTIONS, "--name-status", *range_revs(args))

    files: list[str] = []
    seen: set[str] = set()
    for line in out.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        if status.startswith("D"):
            continue
        # For rename/copy (Rxxx/Cxxx) the destination path is the last field;
        # for A/M/T it is the only path field.
        dest = parts[-1].strip()
        if dest and dest not in seen:
            seen.add(dest)
            files.append(dest)
    return files


def added_lines_by_file(args: argparse.Namespace) -> dict[str, list[str]]:
    """Return added (``+``) content lines grouped by destination file.

    In range mode every commit contributes its own patch, so a line that was
    added and later removed inside the range is still inspected.
    """
    if args.staged:
        out = run("git", "diff", "--cached", "--text", "--unified=0")
    else:
        out = run(
            "git", "log", *LOG_OPTIONS, "--patch", "--text", "--unified=0", *range_revs(args)
        )

    added: dict[str, list[str]] = {}
    current = ""
    for line in out.splitlines():
        if line.startswith("+++ "):
            target = line[4:].strip()
            current = "" if target == "/dev/null" else target[2:] if target.startswith("b/") else target
            continue
        if line.startswith("+") and not line.startswith("+++"):
            if current:
                added.setdefault(current, []).append(line[1:])
    return added


def is_allowed(path: str, name: str) -> bool:
    return any(
        fnmatch.fnmatch(path, glob) or fnmatch.fnmatch(name, glob)
        for glob in ALLOWED_PATH_GLOBS
    )


def check_blocked_paths(files: list[str], blocked_dirs: frozenset[str]) -> list[str]:
    offences: list[str] = []
    for path in files:
        name = PurePosixPath(path).name
        if is_allowed(path, name):
            continue
        parts = set(PurePosixPath(path).parts)
        if parts & blocked_dirs:
            offences.append(f"{path} (host-only data directory)")
            continue
        for glob in BLOCKED_PATH_GLOBS:
            if fnmatch.fnmatch(path, glob) or fnmatch.fnmatch(name, glob):
                offences.append(f"{path} (blocked secret/credential file)")
                break
    return offences


def check_secret_canary(added: dict[str, list[str]]) -> list[str]:
    offences: list[str] = []
    for path, lines in added.items():
        for line in lines:
            for label, pattern in SECRET_CONTENT_PATTERNS:
                if pattern.search(line):
                    offences.append(f"{path}: {label}")
                    break
    return offences


def guard(args: argparse.Namespace) -> int:
    blocked_dirs = BLOCKED_DIR_PARTS | load_overlay_dir_parts()

    if args.staged:
        scope = "staged index"
    else:
        revs = range_revs(args)
        scope = f"{count_commits(revs)} commit(s), each scanned individually"

    files = changed_files(args)
    if not files:
        print(f"Push safety guard: no changed files ({scope}).")
        return 0

    path_offences = check_blocked_paths(files, blocked_dirs)
    secret_offences = check_secret_canary(added_lines_by_file(args))

    if path_offences or secret_offences:
        print("ERROR: push safety guard blocked this change.", file=sys.stderr)
        if path_offences:
            print("Blocked paths (must never be committed):", file=sys.stderr)
            for item in sorted(set(path_offences)):
                print(f"- {item}", file=sys.stderr)
        if secret_offences:
            print("Secret canary matched added content (value redacted):", file=sys.stderr)
            for item in sorted(set(secret_offences)):
                print(f"- {item}", file=sys.stderr)
        print("Remove the secret/credential, keep it out of git, and re-stage.", file=sys.stderr)
        return 1

    print(
        f"Push safety guard: OK ({len(files)} changed file(s) over {scope}; "
        "no secrets or blocked paths)."
    )
    return 0


def main() -> int:
    args = parse_args()
    try:
        return guard(args)
    except GuardError as exc:
        print(f"ERROR: push safety guard could not complete: {exc}", file=sys.stderr)
        print("Refusing to report a clean result it did not verify (fail-closed).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
