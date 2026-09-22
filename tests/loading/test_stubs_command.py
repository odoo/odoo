from __future__ import annotations

import ast
import os
import subprocess
import sys

from .conftest import REPO_ROOT, requires_pg

pytestmark = requires_pg


def test_stubs_command_types_a_real_registry(base_db, tmp_path):
    generated = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "stubs",
            "-d",
            base_db,
            "--addons-path",
            f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'}",
            "--output",
            str(tmp_path),
            "--log-level",
            "warn",
        ],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert generated.returncode == 0, generated.stdout + generated.stderr
    stub = tmp_path / "odoo_registry_stubs.pyi"
    assert stub.exists()
    config = tmp_path / "mypy.ini"
    config.write_text(
        "[mypy]\npython_version = 3.14\nfollow_imports = silent\n"
        "ignore_missing_imports = True\n"
        f"cache_dir = {tmp_path / 'cache'}\n"
        f"plugins = {REPO_ROOT / 'mypy_registry_plugin.py'}\n"
    )
    client = tmp_path / "client.py"
    client.write_text(
        "from odoo.api import Environment\n"
        "def use(env: Environment) -> None:\n"
        "    partner = env['res.partner'].search([], limit=1)\n"
        "    partner.address_get(['contact'])\n"
        "    reveal_type(partner.parent_id.name)\n"
        "    partner.adress_get(['contact'])\n"
    )
    checked = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--no-incremental",
            "--config-file",
            str(config),
            str(client),
        ],
        cwd=REPO_ROOT,
        env={**os.environ, "MYPYPATH": str(tmp_path)},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    errors = [line for line in checked.stdout.splitlines() if ": error:" in line]
    assert checked.returncode == 1, checked.stdout + checked.stderr
    assert len(errors) == 1, checked.stdout + checked.stderr
    assert 'has no attribute "adress_get"' in errors[0]
    assert 'Revealed type is "str | Literal[False]"' in checked.stdout


def test_stubs_command_writes_a_parsable_stub_of_the_registry(base_db, tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "stubs",
            "--addons-path",
            f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'}",
            "-d",
            base_db,
            "-o",
            str(tmp_path),
            "--log-level",
            "warn",
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    stub = tmp_path / "odoo_registry_stubs.pyi"
    source = stub.read_text()
    ast.parse(source, str(stub))
    assert "class ResPartner(BaseModel):" in source
    assert '    _name: Literal["res.partner"]' in source
    assert "    parent_id: _F[ResPartner]" in source
    assert "    def address_get(self, adr_pref: Any = ...) -> Any: ..." in source
    assert (
        '    def __getitem__(self, model_name: Literal["res.users"]) -> ResUsers: ...'
        in source
    )
    assert "models" in proc.stderr
