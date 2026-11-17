#!/bin/bash
# Oracle: commit the pending change with the message of the merged fix.
set -euo pipefail
cd /app
git add -A
git commit -q -F /solution/reference_message.txt
