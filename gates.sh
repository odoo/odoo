#!/usr/bin/env bash
# Every hard-zero gate of this checkout in one run, with one exit code.
#
#   ./gates.sh                 lint, the two pytest tiers, bare-env mypy, the doc figures
#   ./gates.sh --fast          lint and the two pytest tiers only
#   ./gates.sh --rust --js     add the cargo checks and the JS toolchain
#   ./gates.sh --ref <rev>     run everything on a detached worktree of <rev>,
#                              which is what the pre-push hook does (.githooks/)
#
# The commands are the ones doc/architecture/gates.md and CLAUDE.md §9 give;
# this file only sequences them and prints a table. A gate that needs a
# database (test_lint, the integration suites) is not here: it needs a name
# for the database and runs by hand.
set -u

usage() { sed -n '2,10p' "$0"; exit 2; }

FAST=0 RUST=0 JS=0 REF=""
while [ $# -gt 0 ]; do
    case "$1" in
        --fast) FAST=1 ;;
        --rust) RUST=1 ;;
        --js) JS=1 ;;
        --ref) shift; REF="${1:-}"; [ -n "$REF" ] || usage ;;
        -h|--help) usage ;;
        *) echo "unknown option: $1" >&2; usage ;;
    esac
    shift
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$REF" ]; then
    TREE="$(mktemp -d "${TMPDIR:-/tmp}/odoo-gates.XXXXXX")/tree"
    git -C "$ROOT" worktree add --detach "$TREE" "$REF" -q || exit 2
    trap 'git -C "$ROOT" worktree remove --force "$TREE" >/dev/null 2>&1; rm -rf "$(dirname "$TREE")"' EXIT
    # a worktree carries no node_modules; the JS toolchain reads the checkout's
    [ -d "$ROOT/node_modules" ] && ln -s "$ROOT/node_modules" "$TREE/node_modules"
else
    TREE="$ROOT"
fi
cd "$TREE" || exit 2

# The venv is not on PATH in a fresh shell (CLAUDE.md §5.3). An activated venv
# wins; otherwise the workspace's canonical one, next to the checkout.
if [ -n "${VIRTUAL_ENV:-}" ]; then
    BIN="$VIRTUAL_ENV/bin"
elif [ -x "$ROOT/../p314o19m/bin/python" ]; then
    BIN="$(cd "$ROOT/../p314o19m/bin" && pwd)"
else
    echo "no virtualenv: activate one or create ../p314o19m (CLAUDE.md §5)" >&2
    exit 2
fi
PYTHON="$BIN/python"

MYPY_PIN="$(sed -n 's/^mypy==\([0-9.]*\).*/\1/p' requirements-dev.txt)"
MYPY_ENV="${XDG_CACHE_HOME:-$HOME/.cache}/odoo-gates/mypy-$MYPY_PIN"

declare -a NAMES STATUSES SECONDS_TAKEN
FAILED=0

run() {
    local name="$1"; shift
    local start=$SECONDS out
    out="$(mktemp)"
    printf '%-34s ' "$name"
    if "$@" >"$out" 2>&1; then
        printf 'ok    %4ds\n' $((SECONDS - start))
        STATUSES+=(ok)
    else
        printf 'FAIL  %4ds\n' $((SECONDS - start))
        STATUSES+=(FAIL)
        FAILED=1
        sed 's/^/    /' "$out" | tail -40
    fi
    NAMES+=("$name")
    SECONDS_TAKEN+=($((SECONDS - start)))
    rm -f "$out"
}

bare_mypy() {
    if [ ! -x "$MYPY_ENV/bin/mypy" ]; then
        python3 -m venv "$MYPY_ENV" && "$MYPY_ENV/bin/pip" install -q "mypy==$MYPY_PIN" || return 1
    fi
    # measured with mypy alone installed: in the shared venv psycopg and the
    # stubs resolve to real types and the reading differs (CLAUDE.md §9.1)
    "$MYPY_ENV/bin/mypy" --no-incremental --config-file mypy.ini "$@"
}

tier2() {
    "$BIN/pytest" -q -p no:cacheprovider \
        odoo/orm/tests odoo/http/tests odoo/db/tests odoo/tools/tests \
        tests/service tests/framework
}

echo "gates on $(git -C "$TREE" rev-parse --short HEAD)${REF:+ ($REF)} — $TREE"
run "ruff check odoo/"            "$BIN/ruff" check odoo/ --no-cache
run "ruff check tests/"           "$BIN/ruff" check tests/ --no-cache
run "ruff format --check tests/"  "$BIN/ruff" format --check tests/
run "pytest tier 1"               "$BIN/pytest" -q -p no:cacheprovider
run "pytest tier 2"               tier2
if [ "$FAST" -eq 0 ]; then
    run "mypy core packages"      bare_mypy -p odoo.orm -p odoo.db -p odoo.libs -p odoo.http -p odoo.service -p odoo.modules
    run "mypy tools, cli, tests"  bare_mypy -p odoo.tools -p odoo.cli -p odoo.tests
    # factcheck_env.sh finds the venv beside the checkout; a --ref worktree
    # under /tmp has none beside it and would fall back to the system python3
    run "doc/architecture figures" env ODOO_VENV_PYTHON="$PYTHON" bash doc/architecture/factcheck.sh
fi
if [ "$RUST" -eq 1 ]; then
    run "cargo fmt"               cargo fmt --all --check --manifest-path crates/Cargo.toml
    run "cargo clippy"            cargo clippy --workspace --manifest-path crates/Cargo.toml -- -D warnings
    run "cargo test"              cargo test --workspace --manifest-path crates/Cargo.toml
fi
if [ "$JS" -eq 1 ]; then
    run "eslint"                  npx eslint .
    run "tsc"                     npx tsc --project tsconfig.json --noEmit
    run "prettier scss"           npx prettier --list-different "**/*.scss"
fi

echo
total=0
for i in "${!NAMES[@]}"; do total=$((total + SECONDS_TAKEN[i])); done
if [ "$FAILED" -eq 0 ]; then
    echo "all ${#NAMES[@]} gates green in ${total}s"
else
    echo "RED: $(for i in "${!NAMES[@]}"; do [ "${STATUSES[i]}" = FAIL ] && printf '%s; ' "${NAMES[i]}"; done)(${total}s)"
fi
exit "$FAILED"
