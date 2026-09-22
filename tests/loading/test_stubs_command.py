from __future__ import annotations

import ast
import subprocess
import sys

from .conftest import REPO_ROOT, requires_pg

pytestmark = requires_pg


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
