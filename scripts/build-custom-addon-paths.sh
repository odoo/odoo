#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CUSTOM_ADDONS_DIR="$ROOT_DIR/custom_addons"
PREFIX="${1:-custom_addons}"
SEPARATOR=""

find "$CUSTOM_ADDONS_DIR" -mindepth 1 -maxdepth 1 -type d | sort | while read -r bundle_dir; do
    if [ -f "$bundle_dir/__manifest__.py" ]; then
        continue
    fi
    manifest_files="$(find "$bundle_dir" -mindepth 2 -maxdepth 2 -type f -name '__manifest__.py' | sort)"
    if [ -z "$manifest_files" ]; then
        continue
    fi
    bundle_name="$(basename "$bundle_dir")"
    # Quarantine known legacy bundles that are outside the Odoo 19 line.
    if [ "$bundle_name" = "l10n_br_fiscal-14.0.28.1.0" ]; then
        continue
    fi
    printf '%s%s/%s' "$SEPARATOR" "$PREFIX" "$bundle_name"
    SEPARATOR=","
done
