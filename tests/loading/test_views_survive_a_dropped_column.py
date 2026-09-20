from __future__ import annotations

import subprocess
import sys
import uuid

import pytest

from .._pg import dropdb_path, pg_reachable, psql_path, repo_root

REPO_ROOT = repo_root()
OWNER, EXTENDER, READER = "probe_owner", "probe_extender", "probe_reader"
VIEW = "probe_reader_report"

requires_pg = pytest.mark.requires_pg
requires_psql = pytest.mark.requires_psql

OWNER_MODEL = """
from odoo import fields, models


class ProbeOwner(models.Model):
    _name = "probe.owner"
    _description = "Owns the table"

    kept = fields.Char()
"""

EXTENDER_MODEL = """
from odoo import fields, models


class ProbeOwner(models.Model):
    _inherit = "probe.owner"
{body}
"""

READER_MODEL = f"""
from odoo import fields, models
from odoo.db.schema import drop_view_if_exists


class ProbeReaderReport(models.Model):
    _name = "probe.reader.report"
    _description = "Answers from a query and keeps a view of it for other readers"
    _auto = False

    kept = fields.Char()

    @property
    def _table_query(self):
        return "SELECT * FROM probe_owner"

    def init(self):
        drop_view_if_exists(self.env.cr, "{VIEW}")
        self.env.cr.execute("CREATE VIEW {VIEW} AS " + self._table_query)
"""

DROP = """
from odoo.db import schema


def migrate(cr, version):
    schema.drop_columns(cr, "probe_owner", ["copied"])
"""


def _write(root, name: str, version: str, depends: list[str], model: str) -> None:
    pkg = root / name
    (pkg / "models").mkdir(parents=True, exist_ok=True)
    (pkg / "__manifest__.py").write_text(
        repr(
            {
                "name": name,
                "version": version,
                "depends": depends,
                "installable": True,
                "license": "LGPL-3",
            }
        ),
        encoding="utf-8",
    )
    (pkg / "__init__.py").write_text("from . import models\n", encoding="utf-8")
    (pkg / "models" / "__init__.py").write_text("from . import m\n", encoding="utf-8")
    (pkg / "models" / "m.py").write_text(model, encoding="utf-8")


def _odoo(db: str, addons: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "--addons-path",
            addons,
            "-d",
            db,
            *args,
            "--stop-after-init",
            "--log-level",
            "warn",
        ],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )


def _scalar(db: str, query: str) -> str:
    return subprocess.run(
        [psql_path(), "-d", db, "-tAc", query],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    ).stdout.strip()


@requires_pg
@requires_psql
def test_a_view_of_a_module_outside_the_upgrade_is_rebuilt(tmp_path_factory):
    """A post-migrate drops a column CASCADE; the view that selected it belongs to
    a module this upgrade never loads, so nothing calls its init() again."""
    if not pg_reachable():
        pytest.skip("no reachable PostgreSQL")
    if dropdb_path() is None or psql_path() is None:
        pytest.skip("psql/dropdb not on PATH")

    extra = tmp_path_factory.mktemp("view_probe_addons")
    addons = f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'},{extra}"
    db = f"odoo_viewprobe_{uuid.uuid4().hex[:12]}"
    try:
        _write(extra, OWNER, "1.0", ["base"], OWNER_MODEL)
        _write(
            extra,
            EXTENDER,
            "1.0",
            [OWNER],
            EXTENDER_MODEL.format(body="\n    copied = fields.Char()\n"),
        )
        installed = _odoo(db, addons, "-i", f"base,{OWNER},{EXTENDER}")
        assert installed.returncode == 0, installed.stderr[-4000:]
        # installed afterwards, so that its SELECT * expands to the extender's column
        _write(extra, READER, "1.0", [OWNER], READER_MODEL)
        installed = _odoo(db, addons, "-i", READER)
        assert installed.returncode == 0, installed.stderr[-4000:]
        assert "copied" in _scalar(db, f"SELECT pg_get_viewdef('{VIEW}'::regclass)")
        assert (
            _scalar(db, f"SELECT count(*) FROM pg_views WHERE viewname = '{VIEW}'")
            == "1"
        )

        _write(
            extra, EXTENDER, "1.1", [OWNER], EXTENDER_MODEL.format(body="\n    pass\n")
        )
        script = extra / EXTENDER / "migrations" / "1.1" / "post-migrate.py"
        script.parent.mkdir(parents=True)
        script.write_text(DROP, encoding="utf-8")
        upgraded = _odoo(db, addons, "-u", EXTENDER)
        assert upgraded.returncode == 0, upgraded.stderr[-4000:]

        assert (
            _scalar(
                db,
                "SELECT count(*) FROM information_schema.columns "
                "WHERE table_name = 'probe_owner' AND column_name = 'copied'",
            )
            == "0"
        ), "the migration did not drop the column"
        assert (
            _scalar(db, f"SELECT count(*) FROM pg_views WHERE viewname = '{VIEW}'")
            == "1"
        ), "the reader's view went with the column and nothing rebuilt it"
    finally:
        subprocess.run([dropdb_path(), "--if-exists", db], check=False, timeout=60)
