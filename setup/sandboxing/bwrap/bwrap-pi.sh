#!/bin/bash
#
# bwrap-pi.sh - Run the pi coding agent inside a bubblewrap sandbox, with the
# ability to run Odoo tests (Python and JavaScript).
#
# Drop-in wrapper for the `pi` CLI. Provides filesystem isolation by
# running pi inside a bubblewrap (bwrap) container. Only explicitly
# allowed directories are visible to pi inside the sandbox.
#
# REQUIREMENTS
#   - bubblewrap (bwrap) installed and available on PATH
#   - pi binary (npm install -g @mariozechner/pi-coding-agent)
#
#   Optional (mounts use bind-try and are silently skipped if absent):
#   - Google Chrome or Chromium (/opt/google/chrome or /snap/chromium)
#   - PostgreSQL (Unix socket at /var/run/postgresql)
#   - Odoo filestore (~/.local/share/Odoo)
#
# USAGE
#   bwrap-pi.sh [--add-dir <path> ...] [pi args...]
#
# OPTIONS
#   --add-dir <path>
#       Bind-mount <path> read-write into the sandbox in addition to the
#       pre-configured Odoo directories. pi does not support --add-dir
#       natively, so these are only used for bwrap bind-mounts. All other
#       arguments are forwarded to pi.
#
# ENVIRONMENT
#   ODOO_BASE          Path to the Odoo workspace (default: ~/src/odoo)
#   PI_BIN             Path to the pi binary (default: auto-detected via PATH)
#   OPENROUTER_API_KEY API key for OpenRouter. pi uses OpenRouter as its
#                      default provider. The script warns at startup if this
#                      variable is not set. Configure the key in
#                      ~/.pi/agent/settings.json or export it in your shell.
#
# SANDBOX LAYOUT
#   Read-write mounts:
#     ~/.pi                        pi config, sessions, and data
#     $ODOO_BASE                   Odoo workspace (community + enterprise)
#     <--add-dir paths>            Extra project directories passed by the caller
#
#   Optional read-write mounts (bind-try, skipped if absent):
#     ~/.local/share/Odoo          Odoo filestore
#     /var/run/postgresql           PostgreSQL Unix socket (local DB access)
#
#   Read-only mounts:
#     /usr (+ /bin, /sbin, /lib, /lib64 symlinks)
#                                  System binaries and libraries
#     /etc/alternatives            Symlink targets (Chrome binary chain)
#     /etc/hosts                   Hostname resolution
#     /etc/passwd                  User database (required for PostgreSQL auth)
#     /etc/ssl                     TLS certificates
#     /run/systemd/resolve         Systemd-resolved DNS
#
#   Optional read-only mounts (bind-try, skipped if absent):
#     /opt/google/chrome           Chrome installation
#     /snap/bin, /snap/chromium    Snap Chromium installation
#     /etc/fonts                   Font configuration
#     ~/.fonts, ~/.local/share/fonts  User fonts
#
#   Ephemeral:
#     /dev                         Device nodes (via --dev)
#     /proc                        Process info (via --proc)
#     /tmp                         Temporary files (tmpfs, cleared on exit)
#
# NAMESPACE ISOLATION
#   Unshared: IPC, UTS, cgroup, PID
#   Shared:
#     - Network: pi requires outbound internet access.
#
# WORKING DIRECTORY
#   The sandbox starts in $ODOO_BASE (i.e. ~/src/odoo by default).
#
# RUNNING ODOO TESTS
#   When running Odoo tests, use the --logfile option to redirect logs to a
#   file inside $ODOO_BASE (e.g. --logfile ~/src/odoo/log/test.log). Hundreds
#   of lines of test output in stdout won't render well in pi's TUI.

set -e

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Do not run this script as root" >&2
  exit 1
fi

HOME="${HOME:-/home/$(whoami)}"
PI_BIN="${PI_BIN:-$(command -v pi 2>/dev/null || true)}"

# Pre-check: ensure pi binary exists
if [[ -z "$PI_BIN" || ! -x "$PI_BIN" ]]; then
  echo "pi coding agent not found." >&2
  echo "Set PI_BIN to the path of the pi binary, or install it:" >&2
  echo "  npm install -g @mariozechner/pi-coding-agent" >&2
  exit 1
fi


# Pre-check: ensure config directory exists
PI_DIRS=(
  "$HOME/.pi"
)
for d in "${PI_DIRS[@]}"; do
  mkdir -p "$d"
done

# Odoo workspace
ODOO_BASE="${ODOO_BASE:-$HOME/src/odoo}"

# Collect allowed dirs from args; intercept --add-dir from args for bwrap binding
ALLOW_DIRS=("$ODOO_BASE")
PI_ARGS=()
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--add-dir" ]]; then
    shift
    ALLOW_DIRS+=("$(cd "$1" && pwd)")
    shift
  else
    PI_ARGS+=("$1")
    shift
  fi
done

# Resolve the real path so we can find the actual binary (not just a symlink)
PI_BIN_REAL="$(readlink -f "$PI_BIN")"

# Determine the npm global prefix to bind-mount (contains the pi binary and its node_modules)
# npm global installs put binaries in <prefix>/dist/ and packages in <prefix>/node_modules/
PI_PREFIX="$(dirname "$(dirname "$PI_BIN_REAL")")"

BWRAP=(
  # pi binary: bind the npm global prefix so the binary and its node_modules are available
  --ro-bind "$PI_PREFIX" "$PI_PREFIX"
  # If the user's pi command is a symlink from a different path (e.g. /usr/local/bin/pi
  # pointing to ~/.npm-global/...), bind that directory too so the symlink resolves.
  # Network-related files
  --ro-bind /run/systemd/resolve /run/systemd/resolve
  --ro-bind /etc/hosts /etc/hosts
  --ro-bind /etc/ssl /etc/ssl
  --symlink ../run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
  # System binaries and libraries
  --ro-bind /usr /usr
  --symlink usr/bin   /bin
  --symlink usr/sbin  /sbin
  --symlink usr/lib   /lib
  --symlink usr/lib64 /lib64
  --dev /dev
  --proc /proc
  --tmpfs /tmp
  # Unshare namespaces to isolate the sandbox
  --chdir "$ODOO_BASE"
  --unshare-all
  --share-net
  --die-with-parent
  --new-session
  --hostname dev-sandbox
  # Odoo: filestore and PostgreSQL socket, passwd necessary for PostgreSQL auth
  --bind-try "$HOME/.local/share/Odoo" "$HOME/.local/share/Odoo"
  --bind-try /var/run/postgresql /var/run/postgresql
  --ro-bind /etc/passwd /etc/passwd
  # Chrome / Chromium installation and symlink chain
  --ro-bind /etc/alternatives /etc/alternatives
  --ro-bind-try /opt/google/chrome /opt/google/chrome
  --ro-bind-try /snap/bin /snap/bin
  --ro-bind-try /snap/chromium /snap/chromium
  # Chrome: fonts
  --ro-bind-try /etc/fonts /etc/fonts
  --ro-bind-try "$HOME/.fonts" "$HOME/.fonts"
  --ro-bind-try "$HOME/.local/share/fonts" "$HOME/.local/share/fonts"
)

# Bind pi config directory
for path in "${PI_DIRS[@]}"; do
  BWRAP+=(--bind "$path" "$path")
done

# Bind allowed directories
for path in "${ALLOW_DIRS[@]}"; do
  BWRAP+=(--bind "$path" "$path")
done

# If PI_BIN is a symlink from outside PI_PREFIX (e.g. /usr/local/bin/pi -> ~/.npm-global/...),
# bind the symlink's parent directory read-only so the command resolves inside the sandbox.
PI_BIN_DIR="$(dirname "$PI_BIN")"
PI_PREFIX_RESOLVED="$(readlink -f "$PI_PREFIX")"
if [[ "$(readlink -f "$PI_BIN_DIR")" != "$PI_PREFIX_RESOLVED"* ]]; then
  BWRAP+=(--ro-bind "$PI_BIN_DIR" "$PI_BIN_DIR")
fi

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "Warning: OPENROUTER_API_KEY is not set" >&2
fi

echo "Running: bwrap ${BWRAP[@]} -- $PI_BIN ${PI_ARGS[@]}" >&2

# Last check before execution: make sure some common $HOME directories are not accessible.
# This could happen if one sets ODOO_BASE as $HOME or $PWD for example.
FORBIDDEN_DIRS=(
  "$HOME/.ssh"
  "$HOME/.gnupg"
)
for dir in "${FORBIDDEN_DIRS[@]}"; do
  if bwrap "${BWRAP[@]}" -- ls "$dir" >/dev/null 2>&1; then
    echo "FAIL: $dir is readable inside the sandbox. Check allowed directories!" >&2
    exit 1
  fi
done

exec bwrap "${BWRAP[@]}" -- "$PI_BIN" "${PI_ARGS[@]}"
