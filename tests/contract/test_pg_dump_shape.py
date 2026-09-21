import re
import subprocess

import pytest

from odoo.service.db._dump_scanner import (
    _ALLOWED_PSQL_META_COMMANDS,
    _refuse_psql_meta_commands,
)

from .._pg import pg_dump_path
from .conftest import requires_pg, requires_pg_dump

_COPY_START = re.compile(r"^COPY .* FROM stdin;\s*$")


def _meta_command_lines(sql: str) -> list[str]:
    out, in_copy = [], False
    for line in sql.split("\n"):
        if in_copy:
            if line == "\\.":
                in_copy = False
            continue
        if _COPY_START.match(line):
            in_copy = True
            continue
        if line.startswith("\\"):
            out.append(line)
    return out


@pytest.fixture(scope="module")
def dump_sql(scratch_db):
    subprocess.run(
        [
            "psql",
            "-d",
            scratch_db,
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            """
        CREATE TABLE t (id serial PRIMARY KEY, txt text);
        INSERT INTO t (txt) VALUES ('a'), (NULL), ('has ; and '' quote');
        CREATE FUNCTION f() RETURNS int AS $$ BEGIN RETURN 1; END; $$
          LANGUAGE plpgsql;
        """,
        ],
        check=True,
        capture_output=True,
    )
    proc = subprocess.run(
        [pg_dump_path(), "--no-owner", scratch_db],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


@requires_pg
@requires_pg_dump
class TestPgDumpMetaCommandShape:
    def test_only_allowlisted_verbs_are_emitted(self, dump_sql):
        sql = dump_sql
        for line in _meta_command_lines(sql):
            verb = line.split(maxsplit=1)[0]
            assert verb in _ALLOWED_PSQL_META_COMMANDS, (
                f"pg_dump emits {verb!r}, which the restore scanner rejects; a "
                f"backup from this pg_dump would refuse to restore. Line: {line!r}"
            )

    def test_every_emitted_argument_matches_its_pinned_pattern(self, dump_sql):
        sql = dump_sql
        for line in _meta_command_lines(sql):
            verb = line.split(maxsplit=1)[0]
            pattern = _ALLOWED_PSQL_META_COMMANDS[verb]
            assert pattern.match(line, len(verb)), (
                f"pg_dump emits {line!r}, whose argument does not match the "
                f"pattern pinned for {verb!r}; real backups would be refused"
            )

    def test_restrict_key_is_alphanumeric(self, dump_sql):
        sql = dump_sql
        keys = [
            line.split(maxsplit=1)[1].strip()
            for line in _meta_command_lines(sql)
            if line.startswith(("\\restrict ", "\\unrestrict "))
        ]
        for key in keys:
            assert re.fullmatch(r"[A-Za-z0-9]+", key), (
                f"pg_dump's restrict key {key!r} is not alphanumeric; the "
                f"scanner's pinned argument pattern is too tight"
            )
        if keys:
            assert len(set(keys)) == 1, "restrict/unrestrict keys must match"

    def test_a_real_dump_passes_the_scanner(self, dump_sql, tmp_path):
        sql = dump_sql
        path = tmp_path / "dump.sql"
        path.write_text(sql, encoding="latin-1")
        _refuse_psql_meta_commands(str(path))
