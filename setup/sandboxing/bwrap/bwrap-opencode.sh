#!/bin/bash
#
# bwrap-opencode.sh - Run Opencode inside a bubblewrap sandbox, with the
# ability to run Odoo tests (Python and JavaScript).
#
# Drop-in wrapper for the `opencode` CLI. Provides filesystem isolation by
# running Opencode inside a bubblewrap (bwrap) container. Only explicitly
# allowed directories are visible to Opencode inside the sandbox.
#
# REQUIREMENTS
#   - bubblewrap (bwrap) installed and available on PATH
#   - Opencode binary at ~/.opencode/bin/opencode
#
#   Optional (mounts use bind-try and are silently skipped if absent):
#   - Google Chrome or Chromium (/opt/google/chrome or /snap/chromium)
#   - PostgreSQL (Unix socket at /var/run/postgresql)
#   - Odoo filestore (~/.local/share/Odoo)
#
# USAGE
#   bwrap-opencode.sh [--add-dir <path> ...] [opencode args...]
#
# OPTIONS
#   --add-dir <path>
#       Bind-mount <path> read-write into the sandbox in addition to the
#       pre-configured Odoo directories. Opencode does not support --add-dir
#       natively, so these are only used for bwrap bind-mounts. All other
#       arguments are forwarded to opencode.
#
# ENVIRONMENT
#   ODOO_BASE      Path to the Odoo workspace (default: ~/src/odoo)
#
# SANDBOX LAYOUT
#   Read-write mounts:
#     ~/.cache/opencode          Opencode cache
#     ~/.config/opencode         Opencode configuration
#     ~/.local/share/opencode    Opencode data
#     ~/.opencode                Opencode binary
#     $ODOO_BASE                 Odoo workspace (community + enterprise)
#     <--add-dir paths>          Extra project directories passed by the caller
#
#   Optional read-write mounts (bind-try, skipped if absent):
#     ~/.local/share/Odoo        Odoo filestore
#     /var/run/postgresql        PostgreSQL Unix socket (local DB access)
#
#   Read-only mounts:
#     /usr (+ /bin, /sbin, /lib, /lib64 symlinks)
#                                System binaries and libraries
#     /etc/alternatives          Symlink targets (Chrome binary chain)
#     /etc/hosts                 Hostname resolution
#     /etc/passwd                User database (required for PostgreSQL auth)
#     /etc/ssl                   TLS certificates
#     /run/systemd/resolve       Systemd-resolved DNS
#
#   Optional read-only mounts (bind-try, skipped if absent):
#     /opt/google/chrome         Chrome installation
#     /snap/bin, /snap/chromium  Snap Chromium installation
#     /etc/fonts                 Font configuration
#     ~/.fonts, ~/.local/share/fonts  User fonts
#
#   Ephemeral:
#     /dev                       Device nodes (via --dev)
#     /proc                      Process info (via --proc)
#     /tmp                       Temporary files (tmpfs, cleared on exit)
#
# NAMESPACE ISOLATION
#   Unshared: IPC, UTS, cgroup, PID
#   Shared:
#     - Network: Opencode requires outbound internet access.
#
# WORKING DIRECTORY
#   The sandbox starts in $ODOO_BASE (i.e. ~/src/odoo by default).
#
# RUNNING ODOO TESTS
#   When running Odoo tests, use the --logfile option to redirect logs to a
#   file inside $ODOO_BASE (e.g. --logfile ~/src/odoo/log/test.log). Hundreds
#   of lines of test output in stdout won't render well in Opencode's TUI.

set -e
HOME="${HOME:-/home/$(whoami)}"
OPENCODE_BIN="${OPENCODE_BIN:-$HOME/.opencode/bin/opencode}"

# Pre-check: ensure Opencode binary exists
if [[ ! -x "$OPENCODE_BIN" ]]; then
  echo "Opencode not found at $OPENCODE_BIN" >&2
  exit 1
fi

# Pre-check: ensure config/cache paths exist
OPENCODE_DIRS=(
  "$HOME/.cache/opencode"
  "$HOME/.config/opencode"
  "$HOME/.local/share/opencode"
  "$HOME/.opencode"
)
for d in "${OPENCODE_DIRS[@]}"; do
  mkdir -p "$d"
done

# Odoo workspace
# We assume the Community and Enterprise source trees are in the same directory.
# For example: $HOME/src/odoo/odoo and $HOME/src/odoo/enterprise
ODOO_BASE="${ODOO_BASE:-$HOME/src/odoo}"

# Collect allowed dirs from args; intercept --add-dir from args for bwrap binding
ALLOW_DIRS=("$ODOO_BASE")
OPENCODE_ARGS=()
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--add-dir" ]]; then
    shift
    ALLOW_DIRS+=("$(cd "$1" && pwd)")
    shift
  else
    OPENCODE_ARGS+=("$1")
    shift
  fi
done

BWRAP=(
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
  # This does not seem to be needed, but keeping it here for future reference.
  # Chrome: D-Bus (system bus + user session bus)
  # --ro-bind-try /etc/machine-id /etc/machine-id
  # --ro-bind-try /run/dbus /run/dbus
  # --bind-try "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus" "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus"
  # Chrome: shared memory for rendering
  # --tmpfs /dev/shm
)

# Bind Opencode config and cache directories
for path in "${OPENCODE_DIRS[@]}"; do
  BWRAP+=(--bind "$path" "$path")
done

# Bind allowed directories
for path in "${ALLOW_DIRS[@]}"; do
  BWRAP+=(--bind "$path" "$path")
done

echo "Running: bwrap ${BWRAP[@]} -- $OPENCODE_BIN ${OPENCODE_ARGS[@]}" >&2
exec bwrap "${BWRAP[@]}" -- "$OPENCODE_BIN" "${OPENCODE_ARGS[@]}"
