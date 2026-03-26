#!/usr/bin/env python3
from __future__ import annotations

import http.client
import json
import os
import ssl
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Header, Log, RichLog, Static


ROOT_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT_DIR / ".env"
LEGACY_ENV_FILE = ROOT_DIR / ".env.make"
DEV_HOST_PID_FILE = ROOT_DIR / "logs" / "odoo-dev-host.pid"
DEV_HOST_LOG_PATH = ROOT_DIR / "logs" / "odoo-dev-host.log"
DEV_PROJECT_PID_FILE = ROOT_DIR / "logs" / "odoo-dev-project.pid"
DEV_PROJECT_LOG_PATH = ROOT_DIR / "logs" / "odoo-dev-project.log"

DEFAULT_ENV = {
    "DOMAIN": "kodoo.online",
    "LOCAL_BIND_HOST": "127.0.0.1",
    "LOCAL_HTTP_PORT": "8069",
    "PUBLIC_HTTP_PORT": "80",
    "PUBLIC_HTTPS_PORT": "443",
    "SMOKE_PUBLIC": "1",
    "TUI_REFRESH_SECONDS": "3",
    "TUI_LOG_LINES": "20",
}

BUTTON_TARGETS = {
    "btn-home": "up-home",
    "btn-cowork": "up-cowork",
    "btn-dev": "up-dev",
    "btn-project": "up-project",
    "btn-db-list": "db-list",
    "btn-refresh-safe": "refresh-safe",
    "btn-stop": "stop",
    "btn-smoke": "smoke",
    "btn-troubleshoot": "troubleshoot",
}

CONTAINERS = {
    "db": "kodoo-db",
    "odoo": "kodoo-odoo",
    "nginx": "kodoo-nginx",
    "ollama": "kodoo-ollama",
    "cloudflared": "kodoo-cloudflared",
}


@dataclass
class ServiceRow:
    name: str
    state: str
    health: str
    published: str


@dataclass
class EndpointRow:
    name: str
    url: str
    status: str
    detail: str


@dataclass
class DatabaseRow:
    name: str
    backend: str
    owner: str
    size: str
    tags: str


@dataclass
class Snapshot:
    mode: str
    summary: str
    files: str
    services: list[ServiceRow]
    endpoints: list[EndpointRow]
    databases: list[DatabaseRow]
    runtime_log: list[str]


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and value[0] in {'"', "'"} and value[-1:] == value[0]:
            value = value[1:-1]
        values[key] = value
    return values


def merged_env() -> dict[str, str]:
    env = dict(DEFAULT_ENV)
    if ENV_FILE.exists():
        env.update(load_env_file(ENV_FILE))
    elif LEGACY_ENV_FILE.exists():
        env.update(load_env_file(LEGACY_ENV_FILE))
    env.update({key: value for key, value in os.environ.items() if value})
    return env


def run_command(
    args: list[str],
    timeout: int = 10,
    env_values: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    try:
        completed = subprocess.run(
            args,
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env_values or os.environ.copy(),
        )
        return completed.returncode, completed.stdout.strip(), completed.stderr.strip()
    except subprocess.TimeoutExpired as exc:
        return 124, (exc.stdout or "").strip(), f"timeout after {timeout}s"
    except FileNotFoundError as exc:
        return 127, "", str(exc)


def pid_running(path: Path) -> bool:
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def inspect_container(container_name: str) -> ServiceRow:
    code, stdout, stderr = run_command(["docker", "inspect", container_name], timeout=6)
    if code != 0:
        detail = stderr or "missing"
        return ServiceRow(container_name, "missing", "-", detail)
    try:
        container = json.loads(stdout)[0]
    except (IndexError, json.JSONDecodeError):
        return ServiceRow(container_name, "unknown", "-", "invalid inspect output")
    state = container.get("State", {})
    status = state.get("Status", "unknown")
    health = state.get("Health", {}).get("Status", "-")
    ports = container.get("NetworkSettings", {}).get("Ports") or {}
    published: list[str] = []
    for container_port, bindings in sorted(ports.items()):
        if not bindings:
            continue
        for binding in bindings:
            host_ip = binding.get("HostIp", "")
            host_port = binding.get("HostPort", "")
            published.append(f"{host_ip}:{host_port}->{container_port}")
    return ServiceRow(container_name, status, health, ", ".join(published) or "-")


def probe_http(url: str, websocket: bool = False, host_header: str | None = None) -> tuple[str, str]:
    parsed = urlparse(url)
    scheme = parsed.scheme or "http"
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    headers = {
        "Host": host_header or parsed.netloc or host,
        "User-Agent": "kodoo-tui/1.0",
    }
    if websocket:
        headers.update(
            {
                "Connection": "Upgrade",
                "Upgrade": "websocket",
                "Sec-WebSocket-Version": "13",
                "Sec-WebSocket-Key": "SGVsbG8sIHdvcmxkIQ==",
            }
        )
    try:
        if scheme == "https":
            if host in {"127.0.0.1", "localhost"} or host.startswith("127."):
                context = ssl._create_unverified_context()
            else:
                context = ssl.create_default_context()
            connection = http.client.HTTPSConnection(host, port, timeout=6, context=context)
        else:
            connection = http.client.HTTPConnection(host, port, timeout=6)
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        location = response.getheader("Location")
        response.read(128)
        detail = response.reason or "-"
        if location:
            detail = f"{detail} -> {location}"
        return str(response.status), detail
    except Exception as exc:
        return "ERR", f"{exc.__class__.__name__}: {exc}"
    finally:
        try:
            connection.close()
        except Exception:
            pass


def detect_mode(service_map: dict[str, ServiceRow], env: dict[str, str]) -> str:
    cloudflared = service_map["cloudflared"]
    nginx = service_map["nginx"]
    odoo = service_map["odoo"]
    if pid_running(DEV_PROJECT_PID_FILE):
        return "project"
    if pid_running(DEV_HOST_PID_FILE):
        return "dev-host"
    if cloudflared.state == "running":
        return "cowork"
    if nginx.state == "running":
        published = nginx.published
        local_port = env["LOCAL_HTTP_PORT"]
        public_port = env["PUBLIC_HTTP_PORT"]
        if f"127.0.0.1:{local_port}->80/tcp" in published or f"{env['LOCAL_BIND_HOST']}:{local_port}->80/tcp" in published:
            return "dev"
        if f"0.0.0.0:{public_port}->80/tcp" in published or f"::{public_port}->80/tcp" in published:
            return "home"
        return "nginx-only"
    if odoo.state == "running":
        return "insecure"
    return "stopped"


def collect_runtime_log(mode: str, lines: int) -> list[str]:
    if mode == "project" and DEV_PROJECT_LOG_PATH.exists():
        combined = [
            f"[host-odoo] {line}"
            for line in DEV_PROJECT_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        ]
        code, stdout, _ = run_command(["docker", "logs", "--tail", str(lines), "kodoo-db"], timeout=6)
        if code == 0 and stdout:
            combined.extend(f"[kodoo-db] {line}" for line in stdout.splitlines()[-lines:])
        return combined[-max(lines, 1) :]
    if mode == "dev-host" and DEV_HOST_LOG_PATH.exists():
        return DEV_HOST_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    log_lines: list[str] = []
    for name in ("kodoo-odoo", "kodoo-nginx", "kodoo-cloudflared"):
        code, stdout, _ = run_command(["docker", "logs", "--tail", str(lines), name], timeout=6)
        if code != 0 or not stdout:
            continue
        for line in stdout.splitlines()[-lines:]:
            log_lines.append(f"[{name}] {line}")
    return log_lines[-max(lines, 1) :]


def database_tags(name: str, env: dict[str, str]) -> str:
    tagged: list[str] = []
    if name == env.get("PROD_DB_NAME", "kodoo"):
        tagged.append("prod")
    if name == env.get("DEV_HOST_DB", "kodoo"):
        tagged.append("dev-host")
    if name == env.get("DEV_HOST_TEST_DB", "ktest"):
        tagged.append("ktest")
    if name == env.get("DEV_PROJECT_DB", "ktest"):
        tagged.append("project")
    return ", ".join(tagged) or "-"


def collect_database_rows(service_map: dict[str, ServiceRow], env: dict[str, str]) -> list[DatabaseRow]:
    db_user = env.get("PROD_DB_USER") or env.get("PG_LOCAL_USER") or "kodoo"
    query = (
        "SELECT datname, pg_get_userbyid(datdba), "
        "pg_size_pretty(pg_database_size(datname)) "
        "FROM pg_database WHERE datistemplate = false ORDER BY datname;"
    )
    if service_map["db"].state == "running":
        code, stdout, stderr = run_command(
            [
                "docker",
                "exec",
                "-i",
                CONTAINERS["db"],
                "psql",
                "-U",
                db_user,
                "-d",
                "postgres",
                "-At",
                "-F",
                "|",
                "-c",
                query,
            ],
            timeout=8,
        )
        backend = "docker"
    else:
        local_env = os.environ.copy()
        db_password = env.get("PG_LOCAL_PASSWORD") or env.get("PROD_DB_PASSWORD") or ""
        if db_password:
            local_env["PGPASSWORD"] = db_password
        code, stdout, stderr = run_command(
            [
                "psql",
                "-h",
                env.get("PG_LOCAL_HOST", "127.0.0.1"),
                "-p",
                env.get("PG_LOCAL_PORT", "5432"),
                "-U",
                env.get("PG_LOCAL_USER", db_user),
                "-d",
                "postgres",
                "-At",
                "-F",
                "|",
                "-c",
                query,
            ],
            timeout=8,
            env_values=local_env,
        )
        backend = "local"
    if code != 0:
        detail = stderr or "database backend unavailable"
        return [DatabaseRow("-", backend, "-", "-", detail)]
    rows: list[DatabaseRow] = []
    for raw_line in stdout.splitlines():
        if not raw_line:
            continue
        parts = raw_line.split("|", 2)
        name = parts[0]
        owner = parts[1] if len(parts) > 1 else "-"
        size = parts[2] if len(parts) > 2 else "-"
        rows.append(DatabaseRow(name, backend, owner or "-", size or "-", database_tags(name, env)))
    if rows:
        return rows
    return [DatabaseRow("-", backend, "-", "-", "no databases found")]


def build_snapshot(env: dict[str, str]) -> Snapshot:
    service_map = {name: inspect_container(container) for name, container in CONTAINERS.items()}
    services = [
        ServiceRow(name, row.state, row.health, row.published)
        for name, row in service_map.items()
    ]

    mode = detect_mode(service_map, env)
    domain = env["DOMAIN"]
    local_bind_host = env["LOCAL_BIND_HOST"]
    local_port = env["LOCAL_HTTP_PORT"]
    endpoints: list[EndpointRow] = []
    local_candidates = [
        f"http://{local_bind_host}:{local_port}/odoo",
        "http://127.0.0.1/odoo",
        "https://127.0.0.1/odoo",
    ]
    chosen_local_base = ""
    for index, url in enumerate(local_candidates, start=1):
        status, detail = probe_http(url)
        endpoints.append(EndpointRow(f"local-{index}", url, status, detail))
        if not chosen_local_base and status in {"200", "303"}:
            chosen_local_base = url.rsplit("/odoo", 1)[0]
    if chosen_local_base:
        ws_url = f"{chosen_local_base}/websocket/health"
        status, detail = probe_http(ws_url, websocket=False, host_header=domain)
        endpoints.append(EndpointRow("websocket", ws_url, status, detail))
    else:
        endpoints.append(
            EndpointRow(
                "websocket",
                f"http://{local_bind_host}:{local_port}/websocket/health",
                "SKIP",
                "no healthy local base",
            )
        )
    public_url = f"https://{domain}"
    if env.get("SMOKE_PUBLIC", "1") == "1":
        status, detail = probe_http(public_url)
        endpoints.append(EndpointRow("public", public_url, status, detail))
    else:
        endpoints.append(EndpointRow("public", public_url, "SKIP", "SMOKE_PUBLIC=0"))

    env_file_ok = "yes" if ENV_FILE.exists() or LEGACY_ENV_FILE.exists() else "no"
    prod_config_ok = "yes" if (ROOT_DIR / "deploy/odoo/kodoo.prod.local.conf").exists() else "no"
    dev_config_ok = "yes" if (ROOT_DIR / "deploy/odoo/kodoo.dev-host.local.conf").exists() else "no"
    project_config_ok = "yes" if (ROOT_DIR / "deploy/odoo/kodoo.dev-project.local.conf").exists() else "no"
    cloudflared_running = service_map["cloudflared"].state == "running"
    summary = "\n".join(
        [
            f"Mode: {mode}",
            f"Domain: {domain}",
            f"Public check: {'on' if env.get('SMOKE_PUBLIC', '1') == '1' else 'off'}",
            f"Local URL: http://{local_bind_host}:{local_port}",
            f"Public URL: https://{domain}",
            f"Cloudflared: {'running' if cloudflared_running else 'stopped'}",
            f"Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ]
    )
    files = "\n".join(
        [
            f".env: {env_file_ok}",
            f"prod config: {prod_config_ok}",
            f"dev-host config: {dev_config_ok}",
            f"project config: {project_config_ok}",
            f"dev-host pid: {'yes' if pid_running(DEV_HOST_PID_FILE) else 'no'}",
            f"project pid: {'yes' if pid_running(DEV_PROJECT_PID_FILE) else 'no'}",
            f"log lines: {env.get('TUI_LOG_LINES', '20')}",
            "DB manager: make db-manager",
            "Actions: h home | c cowork | d dev | p project | b db-list | u refresh-safe | x stop | s smoke | t troubleshoot",
        ]
    )
    databases = collect_database_rows(service_map, env)
    runtime_log = collect_runtime_log(mode, int(env.get("TUI_LOG_LINES", "20")))
    return Snapshot(mode, summary, files, services, endpoints, databases, runtime_log)


class KodooTUI(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #actions {
        height: auto;
        padding: 0 1;
    }

    #actions Button {
        margin: 0 1 1 0;
        min-width: 14;
    }

    #overview,
    #tables,
    #databases-row,
    #logs {
        height: 1fr;
        padding: 0 1 1 1;
    }

    .panel {
        border: round $accent;
        padding: 0 1;
        width: 1fr;
        height: 1fr;
    }

    #summary,
    #files {
        content-align: left top;
    }

    DataTable {
        height: 1fr;
    }

    #activity,
    #runtime-log {
        height: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh_now", "Refresh"),
        ("h", "run_target('up-home')", "Home"),
        ("c", "run_target('up-cowork')", "Cowork"),
        ("d", "run_target('up-dev')", "Dev"),
        ("p", "run_target('up-project')", "Project"),
        ("b", "run_target('db-list')", "DB List"),
        ("u", "run_target('refresh-safe')", "Safe Refresh"),
        ("x", "run_target('stop')", "Stop"),
        ("s", "run_target('smoke')", "Smoke"),
        ("t", "run_target('troubleshoot')", "Troubleshoot"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.env = merged_env()
        self.refresh_seconds = float(self.env.get("TUI_REFRESH_SECONDS", "3"))
        self.command_thread: threading.Thread | None = None
        self.refresh_thread: threading.Thread | None = None
        self.command_running = False
        self.active_mode = "stopped"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="actions"):
            yield Button("Up Home", id="btn-home", variant="primary")
            yield Button("Up Cowork", id="btn-cowork", variant="success")
            yield Button("Up Dev", id="btn-dev", variant="default")
            yield Button("Up Project", id="btn-project", variant="default")
            yield Button("DB List", id="btn-db-list", variant="default")
            yield Button("Safe Refresh", id="btn-refresh-safe", variant="warning")
            yield Button("Stop", id="btn-stop", variant="error")
            yield Button("Smoke", id="btn-smoke", variant="warning")
            yield Button("Troubleshoot", id="btn-troubleshoot")
        with Horizontal(id="overview"):
            yield Static(id="summary", classes="panel")
            yield Static(id="files", classes="panel")
        with Horizontal(id="tables"):
            yield DataTable(id="services", classes="panel")
            yield DataTable(id="endpoints", classes="panel")
        with Horizontal(id="databases-row"):
            yield DataTable(id="databases", classes="panel")
        with Horizontal(id="logs"):
            yield RichLog(id="activity", classes="panel", wrap=True, highlight=False, markup=False)
            yield Log(id="runtime-log", classes="panel")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Kodoo Diagnostics"
        self.sub_title = "Live diagnostics and mode control"
        services = self.query_one("#services", DataTable)
        services.add_columns("Service", "State", "Health", "Published")
        endpoints = self.query_one("#endpoints", DataTable)
        endpoints.add_columns("Probe", "URL", "Status", "Detail")
        databases = self.query_one("#databases", DataTable)
        databases.add_columns("Database", "Backend", "Owner", "Size", "Tags")
        self.log_activity("TUI ready.")
        self.log_activity("Use the buttons or h/c/d/p/b/u/x/s/t.")
        self.set_interval(self.refresh_seconds, self.schedule_refresh)
        self.schedule_refresh()

    def log_activity(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.query_one("#activity", RichLog).write(f"[{timestamp}] {message}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        target = BUTTON_TARGETS.get(event.button.id or "")
        if target:
            self.action_run_target(target)

    def action_refresh_now(self) -> None:
        self.schedule_refresh(force=True)

    def action_run_target(self, target: str) -> None:
        target = self._resolve_target(target)
        if self.command_running:
            self.log_activity(f"Command already running. Ignored: make {target}")
            return
        self.command_thread = threading.Thread(target=self._run_target, args=(target,), daemon=True)
        self.command_thread.start()

    def _resolve_target(self, target: str) -> str:
        mode_target_map = {
            "home": {"smoke": "smoke-home", "troubleshoot": "troubleshoot-home"},
            "cowork": {"smoke": "smoke-cowork", "troubleshoot": "troubleshoot-cowork"},
            "dev": {"smoke": "smoke-dev", "troubleshoot": "troubleshoot-dev"},
            "project": {"smoke": "smoke-project", "troubleshoot": "troubleshoot-project"},
        }
        return mode_target_map.get(self.active_mode, {}).get(target, target)

    def _run_target(self, target: str) -> None:
        env = os.environ.copy()
        env.update(self.env)
        self.call_from_thread(self._set_command_running, True)
        self.call_from_thread(self.log_activity, f"Running: make {target}")
        process = subprocess.Popen(
            ["make", target],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            self.call_from_thread(
                self.query_one("#activity", RichLog).write,
                line.rstrip(),
            )
        return_code = process.wait()
        self.call_from_thread(self.log_activity, f"make {target} exited with code {return_code}")
        self.call_from_thread(self._set_command_running, False)
        self.call_from_thread(self.schedule_refresh, True)

    def _set_command_running(self, running: bool) -> None:
        self.command_running = running
        for button_id in BUTTON_TARGETS:
            self.query_one(f"#{button_id}", Button).disabled = running

    def schedule_refresh(self, force: bool = False) -> None:
        if self.refresh_thread and self.refresh_thread.is_alive() and not force:
            return
        self.refresh_thread = threading.Thread(target=self._refresh_snapshot, daemon=True)
        self.refresh_thread.start()

    def _refresh_snapshot(self) -> None:
        snapshot = build_snapshot(self.env)
        self.call_from_thread(self._apply_snapshot, snapshot)

    def _apply_snapshot(self, snapshot: Snapshot) -> None:
        self.active_mode = snapshot.mode
        self.query_one("#summary", Static).update(snapshot.summary)
        self.query_one("#files", Static).update(snapshot.files)
        services_table = self.query_one("#services", DataTable)
        services_table.clear()
        for row in snapshot.services:
            services_table.add_row(row.name, row.state, row.health, row.published)
        endpoints_table = self.query_one("#endpoints", DataTable)
        endpoints_table.clear()
        for row in snapshot.endpoints:
            endpoints_table.add_row(row.name, row.url, row.status, row.detail)
        databases_table = self.query_one("#databases", DataTable)
        databases_table.clear()
        for row in snapshot.databases:
            databases_table.add_row(row.name, row.backend, row.owner, row.size, row.tags)
        runtime_log = self.query_one("#runtime-log", Log)
        runtime_log.clear()
        lines = snapshot.runtime_log or ["No runtime logs available."]
        for line in lines:
            runtime_log.write_line(line)


if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    KodooTUI().run()
