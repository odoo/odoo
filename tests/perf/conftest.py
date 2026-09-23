from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from .._pg import dropdb_path, pg_reachable, repo_root
from ._bench import calibration_ms

REPO_ROOT = repo_root()
FLOORS = Path(__file__).with_name("floors.json")
ADDONS_PATH = f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'}"

# a time floor is one machine's; the tolerance absorbs a busy neighbour, a
# regression of a fifth does not hide under it
TIME_TOLERANCE = float(os.environ.get("ODOO_PERF_TOLERANCE", "0.25"))

# a time floor is judged only on a machine running at the speed it was set on:
# measured 2026-09-22, the same code read 51 ms and 127 ms an hour apart as the
# CPUs throttled under other work, and dividing by a calibration loop
# over-corrected (the loop slowed 3x where the ORM slowed 1.9x), so a slower
# machine is reported as not judged rather than red
CALIBRATION_KEY = "calibration_ms"

_READINGS = pytest.StashKey[list[dict]]()
_DATABASES = pytest.StashKey[list[dict]]()


def pytest_addoption(parser):
    parser.addoption("--perf-counts-only", action="store_true")
    parser.addoption("--perf-output", default=None)


def pytest_configure(config):
    config.stash[_READINGS] = []
    config.stash[_DATABASES] = []


def pytest_sessionfinish(session, exitstatus):
    output = session.config.getoption("--perf-output")
    if output:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "diff", "HEAD", "--binary"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        ).stdout
        Path(output).write_text(
            json.dumps(
                {
                    "revision": revision,
                    "tracked_diff_sha256": hashlib.sha256(diff).hexdigest(),
                    "tracked_changes": bool(diff),
                    "python": platform.python_version(),
                    "platform": platform.platform(),
                    "counts_only": session.config.getoption("--perf-counts-only"),
                    "exitstatus": int(exitstatus),
                    "readings": session.config.stash[_READINGS],
                    "databases": session.config.stash[_DATABASES],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


def load_floors() -> dict:
    return json.loads(FLOORS.read_text())


def _check(
    scenario: str,
    readings: dict[str, float],
    *,
    counts_only: bool,
    calibration: float | None = None,
    floors_data: dict | None = None,
) -> bool:
    floors_data = load_floors() if floors_data is None else floors_data
    floors = floors_data.get(scenario)
    line = " ".join(f"{k}={v}" for k, v in readings.items())
    print(f"\n[perf] {scenario}: {line}")
    assert floors is not None, (
        f"{scenario} has no floor in {FLOORS.name}; add {json.dumps(readings)}"
    )
    reference = floors_data.get(CALIBRATION_KEY)
    time_judged = not counts_only
    if time_judged and reference and calibration is not None:
        time_judged = calibration <= reference * (1 + TIME_TOLERANCE)
        if not time_judged:
            print(
                f"[perf] {scenario}: time floors not judged -- calibration reads "
                f"{calibration} ms against {reference} ms when the floors were set"
            )
    for key, floor in floors.items():
        assert key in readings, f"{scenario}.{key} was not measured"
        value = readings[key]
        if key.startswith(("statements", "calls")):
            assert value == floor, (
                f"{scenario}.{key} reads {value}, floor {floor}: an exact ratchet, "
                f"move the floor in the same change"
            )
            if key == "statements":
                assert (
                    readings["statements_min"] == readings["statements_max"] == floor
                ), (
                    f"{scenario}: statement counts varied between "
                    f"{readings['statements_min']} and {readings['statements_max']}; "
                    f"expected {floor} for every operation"
                )
        elif time_judged:
            assert value <= floor * (1 + TIME_TOLERANCE), (
                f"{scenario}.{key} reads {value}, floor {floor} "
                f"(+{TIME_TOLERANCE:.0%} allowed)"
            )
    return time_judged


@pytest.fixture
def check(request):
    def checked(scenario, readings):
        counts_only = request.config.getoption("--perf-counts-only")
        calibration = None if counts_only else calibration_ms()
        reading = {"scenario": scenario, **readings, CALIBRATION_KEY: calibration}
        request.config.stash[_READINGS].append(reading)
        reading["time_judged"] = _check(
            scenario, readings, counts_only=counts_only, calibration=calibration
        )

    return checked


@pytest.fixture(scope="session", autouse=True)
def odoo_config(tmp_path_factory):
    from odoo.tools import config

    config.parse_config(
        ["--addons-path", ADDONS_PATH, "--data-dir", str(tmp_path_factory.mktemp("d"))],
        setup_logging=False,
    )
    return config


def pytest_sessionstart(session):
    if not pg_reachable():
        raise pytest.UsageError("performance gates require PostgreSQL")
    if dropdb_path() is None:
        raise pytest.UsageError("performance gates require dropdb")


def _install(modules: str, label: str, pytest_config):
    name = f"odoo_perf_{label}_{uuid.uuid4().hex[:10]}"
    from odoo.tools import config

    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "odoo-bin"),
                "--addons-path",
                ADDONS_PATH,
                "--data-dir",
                config["data_dir"],
                "--load=base,web",
                "--no-http",
                "--max-cron-threads=0",
                "-d",
                name,
                "-i",
                modules,
                "--stop-after-init",
                "--log-level",
                "warn",
            ],
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        if proc.returncode != 0:
            pytest.fail(
                f"could not install {modules}:\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
            )
        import psycopg

        with psycopg.connect(dbname=name) as connection:
            installed = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM ir_module_module WHERE state = 'installed'"
                )
            }
            server_version = connection.execute("SHOW server_version").fetchone()[0]
            model_count = connection.execute(
                "SELECT count(*) FROM ir_model"
            ).fetchone()[0]
        pytest_config.stash[_DATABASES].append(
            {
                "label": label,
                "requested_modules": modules.split(","),
                "installed_modules": sorted(installed),
                "model_count": model_count,
                "server_version": server_version,
            }
        )
        missing = set(modules.split(",")) - installed
        assert not missing, (
            f"{name}: requested modules remain uninstalled: {sorted(missing)}"
        )
        yield name
    finally:
        subprocess.run(
            [dropdb_path(), "--if-exists", "--force", name],
            check=True,
            capture_output=True,
        )


@pytest.fixture(scope="session")
def base_db(odoo_config, request):
    yield from _install("base", "base", request.config)


# the four-module set qualities.md measures: the order flows exercise the
# compute graph, the x2many write path and the confirmation's stock moves
@pytest.fixture(scope="session")
def sale_db(odoo_config, request):
    yield from _install("sale,purchase,stock,account", "sale", request.config)
