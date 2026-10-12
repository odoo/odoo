# Copy this file to ~/.config/firejail
#
# Firejail profile for Claude Code.
#
# Provides filesystem isolation so Claude can only access explicitly
# whitelisted directories. It is intended to run Claude in standalone.
#
# Usage:
#   firejail --profile=claude.profile --whitelist=~/src/odoo claude
#
# LIMITATIONS
#   Firejail always creates a PID namespace, which prevents VSCode IDE
#   integration (`claude /ide`).
#   Use bwrap-claude.sh or the provided code.local if you need the feature.
#
#   ~/.local/bin/claude is a symlink to ~/.local/share/claude/versions/<version>.
#   Auto-updates cannot update the symlink because of the sandboxing. Old
#   binaries are automatically garbage-collected, so after some time the symlink
#   will point to a non-existing executable. To fix the issue, re-install Claude
#   outside of the sandbox:
#     rm -f ~/.local/bin/claude && curl -fsSL https://claude.ai/install.sh | bash


# ============================================================================
# SECURITY HARDENING
# ============================================================================

# Drop capabilities and protocols
# unix is necessary for commnication with postgres through the socket
caps.drop all
nonewprivs
noroot
seccomp
restrict-namespaces
protocol unix,inet,inet6

# No need for this
nodvd
nosound
no3d
notv
nou2f
novideo
nogroups

# Avoid fingerprinting
machine-id
hostname claude-sandbox

# ============================================================================
# FILESYSTEM ISOLATION
# ============================================================================

# Override blacklists from the includes below for paths we need.
# noblacklist must appear before the include that would blacklist the path.
noblacklist ${HOME}/.cache/claude
noblacklist ${HOME}/.cache/claude-cli-nodejs
noblacklist ${HOME}/.claude
noblacklist ${HOME}/.claude.json
noblacklist ${HOME}/.local/bin/claude
noblacklist ${HOME}/.local/share/claude
noblacklist ${HOME}/.local/state/claude

include disable-common.inc
include disable-programs.inc

private-tmp
private-dev
private-etc @network,@tls-ca

disable-mnt

# ============================================================================
# WHITELIST - WRITABLE PATHS
# ============================================================================

mkdir ${HOME}/.cache/claude
mkdir ${HOME}/.cache/claude-cli-nodejs
mkdir ${HOME}/.claude
mkdir ${HOME}/.local/state/claude

whitelist ${HOME}/.cache/claude
whitelist ${HOME}/.cache/claude-cli-nodejs
whitelist ${HOME}/.claude
whitelist ${HOME}/.claude.json
whitelist ${HOME}/.local/bin/claude
whitelist ${HOME}/.local/share/claude
whitelist ${HOME}/.local/state/claude

# ============================================================================
# D-BUS
# ============================================================================

dbus-user none
dbus-system none
