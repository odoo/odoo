from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from .._pg import dependency_plugin, dropdb_path, pg_reachable, repo_root

REPO_ROOT = repo_root()
FLOORS = Path(__file__).with_name("floors.json")
ADDONS_PATH = f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'}"

# a time floor is one machine's; the tolerance absorbs a busy neighbour, a
# regression of a fifth does not hide under it
TIME_TOLERANCE = float(os.environ.get("ODOO_PERF_TOLERANCE", "0.25"))

requires_pg = pytest.mark.requires_pg
REQUIREMENTS = {
    "requires_pg": (pg_reachable, "no reachable PostgreSQL (perf suite needs one)"),
}
pytest_configure, _skip_without_dependencies = dependency_plugin(REQUIREMENTS)


def load_floors() -> dict:
    return json.loads(FLOORS.read_text())


def check(scenario: str, readings: dict[str, float]) -> None:
    floors = load_floors().get(scenario)
    line = " ".join(f"{k}={v}" for k, v in readings.items())
    print(f"\n[perf] {scenario}: {line}")
    assert floors is not None, (
        f"{scenario} has no floor in {FLOORS.name}; add {json.dumps(readings)}"
    )
    for key, value in readings.items():
        floor = floors.get(key)
        assert floor is not None, f"{scenario}.{key} has no floor; reading {value}"
        if key.startswith(("statements", "calls")):
            assert value == floor, (
                f"{scenario}.{key} reads {value}, floor {floor}: an exact ratchet, "
                f"move the floor in the same change"
            )
        else:
            assert value <= floor * (1 + TIME_TOLERANCE), (
                f"{scenario}.{key} reads {value}, floor {floor} "
                f"(+{TIME_TOLERANCE:.0%} allowed)"
            )


@pytest.fixture(scope="session", autouse=True)
def odoo_config(tmp_path_factory):
    from odoo.tools import config

    config.parse_config(
        ["--addons-path", ADDONS_PATH, "--data-dir", str(tmp_path_factory.mktemp("d"))],
        setup_logging=False,
    )
    return config


def _install(modules: str, label: str):
    if not pg_reachable():
        pytest.skip("no reachable PostgreSQL")
    if dropdb_path() is None:
        pytest.skip("dropdb not on PATH")
    name = f"odoo_perf_{label}_{uuid.uuid4().hex[:10]}"
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "--addons-path",
            ADDONS_PATH,
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
        subprocess.run([dropdb_path(), "--if-exists", "--force", name], check=False)
        pytest.fail(
            f"could not install {modules}:\n{proc.stdout[-4000:]}\n{proc.stderr[-4000:]}"
        )
    try:
        yield name
    finally:
        subprocess.run(
            [dropdb_path(), "--if-exists", "--force", name],
            check=False,
            capture_output=True,
        )


@pytest.fixture(scope="session")
def base_db(odoo_config):
    yield from _install("base", "base")


# the four-module set qualities.md measures: the order flows exercise the
# compute graph, the x2many write path and the confirmation's stock moves
@pytest.fixture(scope="session")
def sale_db(odoo_config):
    yield from _install("sale,purchase,stock,account", "sale")
