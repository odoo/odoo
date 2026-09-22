from __future__ import annotations

import subprocess
import sys

import psycopg

from .conftest import REPO_ROOT, requires_pg

pytestmark = requires_pg


def _installed(db: str) -> set[str]:
    with psycopg.connect(dbname=db) as connection:
        rows = connection.execute(
            "SELECT name FROM ir_module_module WHERE state = 'installed'"
        ).fetchall()
    return {name for (name,) in rows}


def _tables(db: str) -> set[str]:
    with psycopg.connect(dbname=db) as connection:
        rows = connection.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ).fetchall()
    return {name for (name,) in rows}


def test_schema_diff_previews_an_install_and_commits_nothing(base_db):
    before_modules, before_tables = _installed(base_db), _tables(base_db)
    assert "uom" not in before_modules
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "schema_diff",
            "--addons-path",
            f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'}",
            "-d",
            base_db,
            "-i",
            "uom",
            "--log-level",
            "warn",
        ],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "DDL statements that would run:" in proc.stdout
    assert "CREATE TABLE" in proc.stdout
    assert "uom" in proc.stdout
    assert _installed(base_db) == before_modules
    assert _tables(base_db) == before_tables


def test_schema_diff_does_not_publish_postcommit_effects(base_db, tmp_path):
    module = tmp_path / "preview_callback"
    module.mkdir()
    marker = tmp_path / "published.txt"
    (module / "__manifest__.py").write_text(
        repr(
            {
                "name": "Preview callback",
                "version": "1.0",
                "depends": ["base"],
                "license": "LGPL-3",
                "post_init_hook": "initialize",
            }
        )
    )
    (module / "__init__.py").write_text(
        "from pathlib import Path\n\n"
        "def initialize(env):\n"
        "    env.cr.execute('CREATE TABLE preview_callback_probe (value integer)')\n"
        f"    env.cr.postcommit.add(lambda: Path({str(marker)!r}).write_text('published'))\n"
    )
    before_modules, before_tables = _installed(base_db), _tables(base_db)
    proc = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "odoo-bin"),
            "schema_diff",
            "--addons-path",
            f"{REPO_ROOT / 'odoo' / 'addons'},{REPO_ROOT / 'addons'},{tmp_path}",
            "-d",
            base_db,
            "-i",
            "preview_callback",
            "--log-level",
            "warn",
        ],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "preview_callback_probe" in proc.stdout
    assert not marker.exists(), "a rolled-back preview published a postcommit effect"
    assert _installed(base_db) == before_modules
    assert _tables(base_db) == before_tables
