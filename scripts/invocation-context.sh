#!/usr/bin/env bash
set -euo pipefail

hostname_short="$(hostname -s 2>/dev/null || hostname 2>/dev/null || echo unknown)"
host_role="${HOST_ROLE:-unknown}"
pwd_now="${PWD:-$(pwd)}"
user_name="${USER:-$(id -un 2>/dev/null || echo unknown)}"
ssh_mode="local"
ssh_peer=""
wsl_mode="no"
tty_state="detached"
parent_cmd=""
context_command="${MAKE_CONTEXT_COMMAND:-}"

if [ -n "${SSH_CONNECTION:-}" ] || [ -n "${SSH_CLIENT:-}" ] || [ -n "${SSH_TTY:-}" ]; then
    ssh_mode="ssh"
    ssh_peer="${SSH_CLIENT:-${SSH_CONNECTION:-unknown}}"
fi

if [ -n "${WSL_DISTRO_NAME:-}" ] || grep -qi microsoft /proc/version 2>/dev/null; then
    wsl_mode="yes"
fi

if [ -t 0 ] || [ -t 1 ]; then
    tty_state="interactive"
fi

parent_cmd="$(ps -o args= -p "${PPID:-0}" 2>/dev/null | sed 's/^[[:space:]]*//' || true)"

if [ -z "${context_command}" ] && [ -n "${MAKECMDGOALS:-}" ]; then
    context_command="make ${MAKECMDGOALS}"
fi

echo "Context:"
echo "  host: ${hostname_short}"
echo "  role: ${host_role}"
echo "  user: ${user_name}"
echo "  pwd: ${pwd_now}"
if [ -n "${context_command}" ]; then
    echo "  command: ${context_command}"
fi
echo "  transport: ${ssh_mode}"
if [ -n "${ssh_peer}" ]; then
    echo "  ssh-peer: ${ssh_peer}"
fi
echo "  tty: ${tty_state}"
echo "  wsl: ${wsl_mode}"
if [ -z "${context_command}" ] && [ -n "${parent_cmd}" ]; then
    echo "  parent: ${parent_cmd}"
fi
