#!/bin/bash
# Oracle: apply the merged stable fix and commit it with its message.
set -euo pipefail
cd /app
git apply /solution/fix.patch
git add -A
git commit -q -F /solution/reference_message.txt
