#!/bin/bash
# Copy the house rules the guidelines judge grades against into the task's
# tests: the odoo-guidelines and odoo-web-guidelines domain files and the
# odoo-security skill, concatenated, each under a header with its path. The
# verifier only sees the task's tests/, never the skills. Rerun after a change
# to those skills:
#     answer_key/sync_guidelines.sh
set -euo pipefail
cd "$(dirname "$0")/.."
SKILLS=../..
OUT=tests/guidelines/rules.md
{
    echo "# The house rules, as the skills state them"
    for f in "$SKILLS"/odoo-guidelines/guidelines/*.md "$SKILLS"/odoo-web-guidelines/guidelines/*.md "$SKILLS"/odoo-security/SKILL.md; do
        echo
        echo "===== ${f#$SKILLS/} ====="
        echo
        cat "$f"
    done
} > "$OUT"
wc -l "$OUT"
