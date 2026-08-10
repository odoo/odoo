# =============================================================================
# install-pre-push.ps1 - Install the pre-push hook that runs ci-check.ps1
# automatically before every `git push`, so CI can never catch you by surprise.
#
#   .\bashs\install-pre-push.ps1
#
# What it does:
#   1. Creates .githooks/pre-push (repo-local and committed)
#   2. Enables core.hooksPath=.githooks so git invokes that file on push
#      (works from any checkout: the hook lives in the repo, not in .git)
#
# The hook runs .\bashs\ci-check.ps1 and blocks the push on any failure.
# Bypass one push:  git push --no-verify
# =============================================================================

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path $PSScriptRoot -Parent
$githooksDir = Join-Path $repoRoot ".githooks"
$githooksPrePush = Join-Path $githooksDir "pre-push"

# --- Hook contents (committed template = the active hook via hooksPath) ----
# Written as an array of lines to avoid here-strings, which some editors
# corrupt on save. The hook itself is a POSIX sh script (runs in Git for
# Windows / WSL / Linux) that invokes our PowerShell checker via powershell.exe.
$hookLines = @(
    '#!/bin/sh',
    '# pre-push - run the local CI mirror (bashs/ci-check.ps1) before every push.',
    '# Managed by bashs/install-pre-push.ps1. Bypass one push: git push --no-verify',
    '',
    'set -e',
    'cd "$(git rev-parse --show-toplevel)"',
    '',
    'echo "Running local CI check (bashs/ci-check.ps1) before push..."',
    'echo "Bypass this check on one push:  git push --no-verify"',
    'echo ""',
    '',
    'if ! powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\bashs\ci-check.ps1"; then',
    '    echo ""',
    '    echo "!!! Local CI check FAILED - push blocked. Fix the errors above, re-run," 1>&2',
    '    echo "    then push again." 1>&2',
    '    exit 1',
    'fi',
    '',
    'echo ""',
    'echo "Local CI check passed - pushing."',
    ''
)

if (-not (Test-Path $githooksPrePush)) {
    New-Item -ItemType Directory -Path $githooksDir -Force | Out-Null
    Set-Content -Path $githooksPrePush -Value $hookLines -Encoding utf8
    Write-Host "Created $githooksPrePush (commit this file to share the hook)" -ForegroundColor Green
}
else {
    Write-Host "$githooksPrePush already exists - not overwriting." -ForegroundColor Yellow
}

# --- Enable hooksPath so THIS repo uses the committed hook ------------------
& git -C $repoRoot config core.hooksPath .githooks

Write-Host ""
Write-Host "Pre-push hook installed and enabled." -ForegroundColor Green
Write-Host "Next push will run:  .\bashs\ci-check.ps1" -ForegroundColor Cyan
Write-Host "If it fails, the push is blocked until you fix it." -ForegroundColor Yellow
Write-Host "One-time bypass:     git push --no-verify" -ForegroundColor Yellow
