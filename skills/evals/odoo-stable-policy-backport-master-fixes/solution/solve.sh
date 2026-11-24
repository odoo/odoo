#!/bin/bash
# Oracle: backport the mrp fix as given, citing its revision; give the planted
# field a label of its own; fix the key in write() and adapt the test to the
# stable signature. The cloud_storage_google error is left alone: the build
# image lacks the library, the code is right.
set -euo pipefail
cd /app
git am --keep-non-patch /home/odoo/patches/0001-*.patch
git commit -q --amend --no-edit --trailer "X-original-commit: df9daf5ea0b5d8f40389757cd8cdc78c81cf17d4"
git apply /solution/fix_label.patch
git add -A && git commit -q -F /solution/message_label.txt
git apply /solution/fix_key_and_test.patch
git add -A && git commit -q -F /solution/message_ddt.txt
