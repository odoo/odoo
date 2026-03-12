# TUI Diagnostics

The live TUI is an optional control plane for the existing `Makefile`.
It does not replace the shell menu; it adds a real-time dashboard on top of the current targets.

## Install

```bash
make tui-install
```

This creates `.venv-tui/` and installs `Textual` from [Textualize/textual](https://github.com/Textualize/textual).

## Run

```bash
make tui
```

Behavior:

- If `Textual` is available, `make tui` opens the live dashboard.
- If `Textual` is missing, it falls back to `scripts/make-tui.sh`.

To force the live dashboard:

```bash
make tui-live
```

## Controls

- `h`: run `make up-home`
- `c`: run `make up-cowork`
- `d`: run `make up-dev`
- `p`: run `make up-project`
- `u`: run `make refresh-safe`
- `x`: run `make stop`
- `s`: run `make smoke`
- `t`: run `make troubleshoot`
- `r`: refresh diagnostics now
- `q`: quit

## Panels

- `Summary`: active mode, URLs, and refresh timestamp
- `Files`: `.env.make`, generated configs, and runtime hints
- `Services`: Docker container state, health, and published ports
- `Endpoints`: local HTTP, websocket, and public HTTP probes
- `Activity`: output from `make` targets launched inside the TUI
- `Runtime log`: recent lines from `odoo`, `nginx`, and `cloudflared`

## Environment

Optional variables in `.env.make`:

```bash
TUI_REFRESH_SECONDS=3
TUI_LOG_LINES=20
```

The TUI also reads the standard stack variables already used by the repository, such as `DOMAIN`, `LOCAL_HTTP_PORT`, and `SMOKE_PUBLIC`.
