# kodoo-tui

`kodoo-tui` is the Go/Bubble Tea cockpit for the repository.
It now centers the operator workflow around runtime state, databases, incidents, and config readiness instead of a generic action catalog.

## Install

```bash
make tui-install
```

This downloads the Go dependencies for `kodoo-tui/` and builds `kodoo-tui/bin/kodoo-tui`.

## Run

```bash
make tui
```

`make tui-live` is still an alias for the same Go TUI.
The backend Makefile remains the operational engine; the redesign changes navigation and UX, not the underlying targets.

## Main Screens

- `1 Overview`: mode, active DB, local/public URLs, service health, smoke, incidents, suggested next step
- `2 Runtime`: operational modes such as Stable Docker, Stable Tunnel, Dev Host, Dev Project, Local Diagnostic / Manager, and Stopped
- `3 Databases`: docker/local database inventory with connectivity, compatibility, and direct actions
- `4 Doctor`: diagnostics by stack modality, prioritizing the current failure and common incident patterns
- `5 Logs`: incident-first view plus raw compose logs
- `6 Config`: setup/validation summary, config values table, edit flow, and config generation actions

## Command Palette

The old launchpad is no longer the default entry surface.
Use `p` to open the command palette / quick switcher for:

- jumping directly to a main screen
- starting key runtime modes
- running smoke or troubleshoot

## Global Keys

- `1`–`6`: jump directly to a main screen
- `tab` / `shift+tab`: switch screens
- `p`: command palette
- `r`: refresh the aggregated snapshot
- `?`: contextual help
- `q` or `ctrl+c`: quit
- `esc`: close help, palette, or the current action overlay

## Overview Shortcuts

- `s`: contextual start/stop
- `w`: open Runtime
- `d`: open Databases
- `l`: open Logs
- `t`: run troubleshoot
- `c`: open Config

## Action Execution

The TUI still executes Make targets through the existing backend.
When an action is triggered, an overlay shows:

- target name and start time
- relevant config values
- database selection when needed
- typed confirmation for destructive actions
- streamed stdout/stderr and completion status

## Config and Environment

The TUI reads `.env` from the repository root and falls back to legacy `.env.make` when needed.
It overlays process environment variables with the same names.

Useful knobs:

```bash
TUI_REFRESH_SECONDS=3
TUI_LOG_LINES=20
```

If `.env` is missing, the TUI still bootstraps it on startup and the Config screen highlights missing required values and generated Odoo config files.
