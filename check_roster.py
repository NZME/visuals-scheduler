#!/usr/bin/env python3
"""
Roster Consistency Check
=========================
Guards against exactly the bug fixed on 2026-09-25: a roster edit that
REPLACES an existing NAME_TO_SLACK_ID entry instead of adding alongside it.

Compares each file's NAME_TO_SLACK_ID (the name -> Slack user ID mapping
used to build @mentions) against the same file's version at the previous
commit. If any name that existed before is missing now, in ANY of the
7 files that carry this mapping, the check fails loudly and names exactly
what disappeared and from which file.

This does not block a genuine, intentional removal (e.g. someone leaving
the team) — it just makes sure that removal is never silent. If a name
needs to come out, remove it, check the run's output confirms only that
name is missing, and note it in the commit message.

Run manually with: python3 check_roster.py
"""
import re
import subprocess
import sys

# Every file that keeps its own copy of the NAME_TO_SLACK_ID roster.
ROSTER_FILES = [
    "api/slack.js",
    "assignment_notifier.py",
    "booking_to_teamup.py",
    "visuals_daily_draft.py",
    "visuals_monday_draft.py",
    "visuals_sunday_draft.py",
    "visuals_today.py",
]

# Matches NAME_TO_SLACK_ID = { ... }, _NAME_TO_SLACK_ID = { ... }, or the JS
# const NAME_TO_SLACK_ID = { ... } — captures everything up to the closing brace.
DICT_BLOCK_RE = re.compile(
    r'(?:const\s+)?_?NAME_TO_SLACK_ID\s*=\s*\{(.*?)\n\}',
    re.DOTALL,
)
KEY_RE = re.compile(r'"([^"]+)"\s*:\s*"[^"]*"')


def extract_names(file_text):
    """Return the set of names in a file's NAME_TO_SLACK_ID block, or None
    if the block wasn't found (e.g. file didn't exist at that revision)."""
    match = DICT_BLOCK_RE.search(file_text)
    if not match:
        return None
    return set(KEY_RE.findall(match.group(1)))


def file_at_revision(path, revision):
    """Return a file's text at a given git revision, or None if it
    doesn't exist there (e.g. the very first commit, or a renamed file)."""
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def main():
    problems = []

    for path in ROSTER_FILES:
        old_text = file_at_revision(path, "HEAD^")
        new_text = file_at_revision(path, "HEAD")

        if new_text is None:
            print(f"  (skip) {path}: not present at HEAD")
            continue
        if old_text is None:
            print(f"  (skip) {path}: no previous revision to compare (new file, or first commit)")
            continue

        old_names = extract_names(old_text)
        new_names = extract_names(new_text)

        if old_names is None or new_names is None:
            problems.append(
                f"{path}: could not find a NAME_TO_SLACK_ID block to check — "
                f"has the dict been renamed or restructured?"
            )
            continue

        removed = old_names - new_names
        if removed:
            problems.append(
                f"{path}: lost {len(removed)} name(s) from NAME_TO_SLACK_ID: "
                f"{', '.join(sorted(removed))}"
            )

    if problems:
        print("\n❌ Roster check FAILED — a name disappeared from NAME_TO_SLACK_ID:\n")
        for p in problems:
            print(f"  - {p}")
        print(
            "\nIf this is intentional (someone left the team), that's fine — "
            "just make sure the run output above lists ONLY the name(s) you "
            "meant to remove, and remove them from every one of the 7 files, "
            "not just this one.\n"
        )
        sys.exit(1)

    print("✅ Roster check passed — no names disappeared from NAME_TO_SLACK_ID.")


if __name__ == "__main__":
    main()
