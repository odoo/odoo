# kodoo-tui

`kodoo-tui` is the Go/Bubble Tea control plane for the repository.
It is now the primary interactive entrypoint for day-to-day environment control.

## Install

```bash
make tui-install
```

This downloads the Go dependencies for `kodoo-tui/` and builds `kodoo-tui/bin/kodoo-tui`.

## Run

```bash
make tui
```

`make tui-live` is an alias for the same Go TUI.

When the TUI opens, it now starts on a **launchpad** screen so you can choose the session mode explicitly:

- **Stable Docker · Public-Sector Runtime**: the stable stack with the public-sector image
- **Stable Docker · Plain Runtime**: the same stable stack with the plain Odoo image
- **Client Dev · Docker DB / Local DB**: ask for the client database first, then boot native Odoo
- **Database Manager · Docker DB / Local DB**: open the Odoo database manager without pinning a client database

The legacy shell menu still exists as an explicit escape hatch:

```bash
make tui-menu
```

## Tabs

- `1 Dashboard`: container state, inferred mode, ports, recent compose events
- `2 Logs`: follow one service or all services with inline search
- `3 Actions`: run grouped Make targets with confirmation and streamed output
- `4 Config`: inspect `.env.make`, open it in `$EDITOR`, and generate Odoo config files

## Global Keys

- `1`–`4`: jump directly to a tab
- `tab` / `shift+tab`: switch tabs
- `l`: reopen the launchpad at any time
- `?`: open contextual help
- `q` or `ctrl+c`: quit
- `esc`: close the current help/action overlay after completion

## Action Output

Any action launched from the TUI opens a lower output panel with:

- the target name and start time
- streaming stdout/stderr
- final completion status
- database selection when the action runs in a per-client mode
- typed confirmation for destructive actions such as `down` and restore flows

## Config and Environment

The TUI reads `.env.make` from the repository root and overlays any process environment variables with the same names.

Useful knobs:

```bash
TUI_REFRESH_SECONDS=3
TUI_LOG_LINES=20
```

If `.env.make` is missing, the dashboard warns and the config tab can create it with `make env-init`.
