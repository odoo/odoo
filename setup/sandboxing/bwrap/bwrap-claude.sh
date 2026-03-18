#!/bin/bash
#
# bwrap-claude.sh - Run Claude Code inside a bubblewrap sandbox, with the
# ability to run Odoo tests (Python and JavaScript).
#
# Drop-in replacement for the `claude` CLI. Provides filesystem isolation by
# running Claude inside a bubblewrap (bwrap) container. Only explicitly
# allowed directories are visible to Claude inside the sandbox.
#
# Odoo Community and Enterprise source trees are pre-mounted. The Odoo
# filestore, PostgreSQL socket, Chrome, and fonts are mounted opportunistically
# with bind-try so the script works even when they are absent.
#
# REQUIREMENTS
#   - bubblewrap (bwrap) installed and available on PATH
#   - Claude Code binary at ~/.local/bin/claude
#
#   Optional (mounts use bind-try and are silently skipped if absent):
#   - Google Chrome or Chromium (/opt/google/chrome or /snap/chromium)
#   - PostgreSQL (Unix socket at /var/run/postgresql)
#   - Odoo filestore (~/.local/share/Odoo)
#
# USAGE
#   bwrap-claude.sh [--add-dir <path> ...] [claude args...]
#
# OPTIONS
#   --add-dir <path>
#       Bind-mount <path> read-write into the sandbox in addition to the
#       pre-configured Odoo directories. Also passed to Claude as --add-dir
#       so its internal tool access matches the sandbox. All other arguments
#       are forwarded to Claude.
#
# ENVIRONMENT
#   ODOO_BASE     Path to the Odoo workspace (default: ~/src/odoo)
#
# SANDBOX LAYOUT
#   Read-write mounts:
#     ~/.cache/claude*          Claude cache directories
#     ~/.claude, ~/.claude.json Claude config and session data
#     ~/.local/bin/claude       Claude binary symlink (allows Claude auto-updates)
#     ~/.local/share/claude     Claude binary versions cache
#     $ODOO_BASE                Odoo workspace (community + enterprise)
#     <--add-dir paths>         Extra project directories passed by the caller
#
#   Optional read-write mounts (bind-try, skipped if absent):
#     ~/.local/share/Odoo       Odoo filestore
#     /var/run/postgresql       PostgreSQL Unix socket (local DB access)
#
#   Read-only mounts:
#     /usr (+ /bin, /sbin, /lib, /lib64 symlinks)
#                               System binaries and libraries. /usr is mounted
#                               whole so VSCode can access /usr/share/code when
#                               Claude is launched from the IDE.
#     /etc/alternatives         Symlink targets (Chrome binary chain)
#     /etc/hosts                Hostname resolution
#     /etc/passwd               User database (required for PostgreSQL auth)
#     /etc/ssl                  TLS certificates
#     /run/systemd/resolve      Systemd-resolved DNS
#
#   Optional read-only mounts (bind-try, skipped if absent):
#     /opt/google/chrome        Chrome installation
#     /snap/bin, /snap/chromium Snap Chromium installation
#     /etc/fonts                Font configuration
#     ~/.fonts, ~/.local/share/fonts  User fonts
#
#   Ephemeral:
#     /dev                      Device nodes (via --dev)
#     /proc                     Process info (via --proc)
#     /tmp                      Temporary files (tmpfs, cleared on exit)
#
# NAMESPACE ISOLATION
#   Unshared: IPC, UTS, cgroup
#   Shared:
#     - Network: Claude requires outbound internet access.
#     - PID: Unsharing PID breaks VSCode's ability to attach to the Claude
#             process for the /ide integration.
#
# WORKING DIRECTORY
#   The sandbox starts in $ODOO_BASE (the first pre-configured allowed dir).
#   This is required for the `claude /ide` command, which validates that the
#   workspace matches the current working directory.
#
# RUNNING ODOO TESTS
#   When running Odoo tests, use the --logfile option to redirect logs to a
#   file inside $ODOO_BASE (e.g. --logfile ~/src/odoo/log/test.log). Hundreds
#   of lines of test output in stdout won't render well in Claude's TUI.
#
# IDE INTEGRATION
#   VSCode Unix domain sockets (vscode-*.sock) found in $XDG_RUNTIME_DIR are
#   bind-mounted into the sandbox so `claude /ide` can connect to the editor.

set -e
HOME="${HOME:-/home/$(whoami)}"
CLAUDE_BIN="${CLAUDE_BIN:-$HOME/.local/bin/claude}"

# Pre-check: ensure Claude binary exists
if [[ ! -x "$CLAUDE_BIN" ]]; then
  echo "Claude Code not found at $CLAUDE_BIN" >&2
  exit 1
fi

# Pre-check: ensure Claude config/cache paths exist
CLAUDE_DIRS=(
  "$HOME/.cache/claude"
  "$HOME/.cache/claude-cli-nodejs"
  "$HOME/.claude"
  "$HOME/.local/state/claude"
)
CLAUDE_FILES=(
  "$HOME/.claude.json"
)
for d in "${CLAUDE_DIRS[@]}"; do
  mkdir -p "$d"
done
for f in "${CLAUDE_FILES[@]}"; do
  [[ -e "$f" ]] || touch "$f"
done

# Odoo workspace
# We assume the Community and Enterprise source trees are in the same directory.
# For example: $HOME/src/odoo/odoo and $HOME/src/odoo/enterprise
ODOO_BASE="${ODOO_BASE:-$HOME/src/odoo}"

# Collect allowed dirs from args; intercept --add-dir from args for bwrap binding
ALLOW_DIRS=("$ODOO_BASE")
CLAUDE_ARGS=()
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--add-dir" ]]; then
    shift
    ALLOW_DIRS+=("$(cd "$1" && pwd)")
    shift
  else
    CLAUDE_ARGS+=("$1")
    shift
  fi
done

BRAP=(
  # Read-write bin (needed for Claude auto-updates). These 2 must already exists since they
  # contain the binaries.
  --bind "$HOME/.local/bin/claude" "$HOME/.local/bin/claude"
  --bind "$HOME/.local/share/claude" "$HOME/.local/share/claude"
  --ro-bind-try "$HOME/.vscode" "$HOME/.vscode"
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
  # Change to the first --add-dir path so `claude /ide` can validate the workspace against the
  # current working directory.
  --chdir "$ODOO_BASE"
  # --unshare-pid => needed for VSCode integration
  --unshare-ipc
  --unshare-uts
  --unshare-cgroup
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
  # Not needed so far, but keeping for future reference.
  # Chrome: D-Bus (system bus + user session bus)
  # --ro-bind-try /etc/machine-id /etc/machine-id
  # --ro-bind-try /run/dbus /run/dbus
  # --bind-try "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus" "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/bus"
  # Chrome: shared memory for rendering
  # --tmpfs /dev/shm
)

# Bind Claude config and cache files
for path in "${CLAUDE_DIRS[@]}" "${CLAUDE_FILES[@]}"; do
  BRAP+=(--bind "$path" "$path")
done

# Bind allowed directories
for path in "${ALLOW_DIRS[@]}"; do
  BRAP+=(--bind "$path" "$path")
done

# Bind VSCode sockets from XDG_RUNTIME_DIR for IDE integration
for sock in "${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"/vscode-*.sock; do
  [[ -S "$sock" ]] && BRAP+=(--bind "$sock" "$sock")
done

# Pass --add-dir for each allowed dir so Claude's tool access matches the sandbox
CLAUDE_CMD=()
for d in "${ALLOW_DIRS[@]}"; do
  CLAUDE_CMD+=(--add-dir "$d")
done
CLAUDE_CMD+=( "${CLAUDE_ARGS[@]}" )

echo "Running: bwrap ${BRAP[@]} -- $CLAUDE_BIN ${CLAUDE_CMD[@]}" >&2
exec bwrap "${BRAP[@]}" -- "$CLAUDE_BIN" "${CLAUDE_CMD[@]}"
