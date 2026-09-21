import pathlib
import tempfile
from unittest.mock import patch

import pytest

from odoo.service.db import _dump_scanner


@pytest.fixture(scope="module")
def db_mod():
    return _dump_scanner


class TestDumpSqlMetaCommandScanner:
    @pytest.mark.parametrize(
        "sql",
        [
            "\\! touch /tmp/pwn\n",
            "SELECT 1;\\! id\n",
            "SELECT 1;\n\\i /etc/passwd\n",
            "SELECT 1 \\gexec\n",
            "\\connect postgres\n",
            "\\o /tmp/out\nSELECT 1;\n",
            "COPY t FROM stdin;\n1\ta\n\\.\n\\! id\n",
        ],
    )
    def test_flags_interpreted_meta_commands(self, db_mod, sql):
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    @pytest.mark.parametrize(
        "sql",
        [
            "SELECT 1;\n",
            "\\restrict TOK\nSELECT 1;\n\\unrestrict TOK\n",
            "COPY t FROM stdin;\n1\tdata\\x\\.more\n\\.\nSELECT 1;\n",
            "CREATE FUNCTION f() AS $$ BEGIN RETURN 'x; \\y'; END; $$ LANGUAGE plpgsql;\n",
            "SELECT E'a\\nb\\\\c';\n",
            "-- a comment with \\! and \\i\nSELECT 1;\n",
            "/* block \\! comment ; \\i */\nSELECT 1;\n",
            "SELECT 'literal ; \\! not a command';\n",
        ],
    )
    def test_allows_data_and_pg_dump_commands(self, db_mod, sql):
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_assert_dump_sql_safe_raises_on_evil_file(self, db_mod):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".sql", delete=False, encoding="utf-8"
        ) as f:
            f.write("\\! touch /tmp/pwn\nSELECT 1;\n")
            path = f.name
        try:
            with pytest.raises(RuntimeError, match="Refusing to restore"):
                db_mod._refuse_psql_meta_commands(path)
        finally:
            pathlib.Path(path).unlink()

    def test_assert_dump_sql_safe_passes_clean_file(self, db_mod):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".sql", delete=False, encoding="utf-8"
        ) as f:
            f.write("\\restrict TOK\nCREATE TABLE t (id int);\n\\unrestrict TOK\n")
            path = f.name
        try:
            db_mod._refuse_psql_meta_commands(path)
        finally:
            pathlib.Path(path).unlink()


class TestDumpSqlScannerStandardConformingStrings:
    def test_flags_the_guc_turned_off(self, db_mod):
        assert (
            db_mod._get_disallowed_psql_meta_command(
                "SET standard_conforming_strings = off;\nSELECT 1;\n"
            )
            is not None
        )

    @pytest.mark.parametrize(
        "sql",
        [
            "SET standard_conforming_strings TO off;\nSELECT 1;\n",
            "SET standard_conforming_strings='off';\nSELECT 1;\n",
            "SET STANDARD_CONFORMING_STRINGS = OFF;\nSELECT 1;\n",
        ],
    )
    def test_flags_every_common_spelling(self, db_mod, sql):
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_allows_the_guc_turned_on(self, db_mod):
        assert (
            db_mod._get_disallowed_psql_meta_command(
                "SET standard_conforming_strings = on;\nSELECT 1;\n"
            )
            is None
        )

    def test_allows_the_phrase_without_off(self, db_mod):
        assert (
            db_mod._get_disallowed_psql_meta_command(
                "SELECT 'standard_conforming_strings is unrelated here';\n"
            )
            is None
        )

    def test_would_otherwise_hide_a_meta_command_behind_a_desynced_string(self, db_mod):
        # Under `off`, an unprefixed backslash escapes the closing quote of a
        # plain string the same way `E'...'` always does, so this whole
        # payload is one string followed by an inert `\!` to real psql. The
        # scanner does not model `off`, so without the guard above it reads
        # the escaped quote as closing the string early and the real closing
        # quote as opening a second, unterminated one -- going blind to the
        # `\!` that follows. The GUC guard must catch this before that
        # divergence ever comes into play.
        payload = "SET standard_conforming_strings = off;\nSELECT 'a\\'b';\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(payload) is not None

    def test_assert_dump_sql_safe_raises_with_its_own_message(self, db_mod):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".sql", delete=False, encoding="utf-8"
        ) as f:
            f.write("SET standard_conforming_strings = off;\nSELECT 1;\n")
            path = f.name
        try:
            with pytest.raises(RuntimeError, match="standard_conforming_strings"):
                db_mod._refuse_psql_meta_commands(path)
        finally:
            pathlib.Path(path).unlink()


class TestDumpSqlMetaCommandArguments:
    @pytest.mark.parametrize(
        "sql",
        [
            "\\restrict `touch /tmp/pwn`\n",
            "\\unrestrict `touch /tmp/pwn`\n",
            "\\restrict /*\n\\unrestrict /*\n\\! id\n",
            "\\restrict $$\n\\unrestrict $$\n\\! id\n",
            "\\restrict '\n\\! id\n",
            '\\restrict "\n\\! id\n',
            "\\unrestrict /*\n\\! id\n",
            "\\. /*\n\\! id\n",
            "\\. `touch /tmp/pwn`\n",
            "\\restrict\n",
            "\\restrict k1 extra\n",
        ],
    )
    def test_flags_malformed_meta_command_arguments(self, db_mod, sql):
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_report_names_the_argument_not_just_the_verb(self, db_mod):
        hit = db_mod._get_disallowed_psql_meta_command("\\restrict `id`\n")
        assert hit is not None
        assert "`id`" in hit[1]

    @pytest.mark.parametrize(
        "sql",
        [
            "\\restrict abc123\nSELECT 1;\n\\unrestrict abc123\n",
            "\\restrict tH7nmJAc12qRGNgZNXhGPXxv78E3UN0d5YagNMhRvb9i2u49YBGiEpyi0gW9RHO\n",
            "\\restrict abc123\r\n",
            "\\restrict abc123",
            "COPY t (a) FROM stdin;\n1\n\\.\nSELECT 1;\n",
        ],
    )
    def test_allows_real_pg_dump_shapes(self, db_mod, sql):
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_argument_text_is_not_lexed_as_sql(self, db_mod):
        sql = "\\restrict k1\nSELECT 1;\n\\! id\n"
        hit = db_mod._get_disallowed_psql_meta_command(sql)
        assert hit == (3, "\\!")


class TestDumpSqlScannerLineBound:
    def _write(self, tmp_path, text):
        p = tmp_path / "dump.sql"
        p.write_text(text, encoding="latin-1")
        return str(p)

    def test_overlong_line_is_refused(self, db_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", str(4 * 1024 * 1024))
        path = self._write(tmp_path, "SELECT '" + "A" * (5 * 1024 * 1024) + "';\n")
        with pytest.raises(RuntimeError, match="longer than"):
            db_mod._refuse_psql_meta_commands(path)

    def test_line_at_the_limit_is_accepted(self, db_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", str(4 * 1024 * 1024))
        path = self._write(tmp_path, "SELECT '" + "A" * (2 * 1024 * 1024) + "';\n")
        db_mod._refuse_psql_meta_commands(path)

    def test_cap_does_not_blind_the_scanner(self, db_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", str(4 * 1024 * 1024))
        path = self._write(
            tmp_path, "\\! touch /tmp/pwn\nSELECT '" + "A" * (9 * 1024 * 1024) + "';\n"
        )
        with pytest.raises(RuntimeError, match="meta-command"):
            db_mod._refuse_psql_meta_commands(path)

    def test_malformed_env_override_falls_back_to_the_default(
        self, db_mod, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", "not-a-number")
        path = self._write(tmp_path, "SELECT 1;\n")
        db_mod._refuse_psql_meta_commands(path)

    def test_overlong_copy_data_line_is_accepted(self, db_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", str(4 * 1024 * 1024))
        big = "QUJD" * (2 * 1024 * 1024)
        path = self._write(
            tmp_path,
            "CREATE TABLE ir_attachment (id int, db_datas text);\n"
            "COPY ir_attachment (id, db_datas) FROM stdin;\n"
            f"1\t{big}\n\\.\nSELECT 1;\n",
        )
        db_mod._refuse_psql_meta_commands(path)

    def test_overlong_copy_data_does_not_blind_a_later_meta_command(
        self, db_mod, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", str(4 * 1024 * 1024))
        big = "QUJD" * (2 * 1024 * 1024)
        path = self._write(
            tmp_path,
            f"COPY t (a) FROM stdin;\n{big}\n\\.\n\\! touch /tmp/pwn\n",
        )
        with pytest.raises(RuntimeError, match="meta-command"):
            db_mod._refuse_psql_meta_commands(path)

    def test_overlong_sql_line_still_refused(self, db_mod, tmp_path, monkeypatch):
        monkeypatch.setenv("ODOO_DUMP_SCAN_MAX_LINE", str(4 * 1024 * 1024))
        path = self._write(tmp_path, "SELECT '" + "A" * (8 * 1024 * 1024) + "';\n")
        with pytest.raises(RuntimeError, match="longer than"):
            db_mod._refuse_psql_meta_commands(path)


class TestDumpSqlScannerLexerDivergence:
    @pytest.mark.parametrize("ident", ["a$b$c", "money$usd$x", "éx$q$z", "_a$t$b"])
    def test_dollar_inside_identifier_does_not_open_a_quoted_body(self, db_mod, ident):
        sql = f"CREATE TABLE {ident} (x int);\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    @pytest.mark.parametrize(
        "expr",
        [
            "SELECT 1 AS 9a$b$c",
            "SELECT 1 AS a1$t$",
            "SELECT 1 AS 0fooE$t$x",
            "SELECT 1 AS ÿ$_$",
            "SELECT 1 AS +9fooE$$z",
        ],
    )
    def test_digit_led_run_restarts_at_the_identifier(self, db_mod, expr):
        sql = f"{expr};\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_number_really_does_open_a_dollar_quote(self, db_mod):
        sql = "SELECT 1$t$ a \\! b $t$;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_missing_a_dollar_body_is_not_a_safe_fallback(self, db_mod):
        run = "1" + "0" * 300
        sql = f"SELECT {run}$$ it's $$\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_dollar_quote_after_a_token_boundary_still_opens(self, db_mod):
        sql = (
            "CREATE FUNCTION f() RETURNS text AS $_$ SELECT 'a; \\! b'; $_$ "
            "LANGUAGE sql;\n"
        )
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_identifier_containing_dollar_is_not_flagged(self, db_mod):
        sql = "CREATE TABLE money$usd (x int);\nINSERT INTO money$usd VALUES (1);\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_copy_from_stdin_without_semicolon_does_not_enter_data_mode(self, db_mod):
        sql = "COPY nosuchtable FROM stdin\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_meta_command_between_copy_and_its_semicolon_is_flagged(self, db_mod):
        sql = "COPY ok FROM stdin\n\\! touch /tmp/pwn\n;\n1\n\\.\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_terminated_copy_still_treats_following_lines_as_data(self, db_mod):
        sql = "COPY t (a,b) FROM stdin;\n1\tdata\\x\\.more\n\\.\nSELECT 1;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_semicolon_inside_copy_options_does_not_arm_data_mode_early(self, db_mod):
        sql = "COPY t FROM stdin WITH (DELIMITER ';');\n1\n\\.\nSELECT 1;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_copy_to_stdout_with_from_stdin_in_line_comment_is_not_data(self, db_mod):
        sql = "COPY (SELECT 1) TO STDOUT; -- FROM stdin\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_copy_to_stdout_with_from_stdin_in_block_comment_is_not_data(self, db_mod):
        sql = "COPY (SELECT 1) TO STDOUT /* FROM stdin */;\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_copy_to_stdout_with_from_stdin_in_string_literal_is_not_data(self, db_mod):
        sql = "COPY (SELECT 'FROM stdin') TO STDOUT;\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_from_stdin_after_the_terminating_semicolon_is_not_data(self, db_mod):
        sql = "COPY (SELECT 1) TO STDOUT; SELECT 'x' FROM stdin\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_statement_not_starting_with_copy_never_enters_data_mode(self, db_mod):
        sql = "SELECT * FROM stdin;\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_quoted_copy_identifier_is_not_the_copy_command(self, db_mod):
        sql = '"COPY" t FROM stdin;\n\\! touch /tmp/pwn\n'
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_copy_from_stdin_is_case_insensitive(self, db_mod):
        sql = "copy T (a) FrOm StDiN;\n1\tdata\\x\n\\.\nSELECT 1;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_copy_preceded_by_a_comment_on_the_same_line_still_enters_data_mode(
        self, db_mod
    ):
        sql = "/* c */ COPY t (a) FROM stdin;\n1\t\\N\n\\.\nSELECT 1;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_copy_from_stdin_spanning_two_lines_still_enters_data_mode(self, db_mod):
        sql = "COPY t (a)\n  FROM stdin;\n1\t\\N\n\\.\nSELECT 1;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_e_prefix_inside_an_identifier_is_not_an_escape_string(self, db_mod):
        sql = "SELECT fooE'x';\n\\! touch /tmp/pwn\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is not None

    def test_real_escape_string_still_swallows_its_backslashes(self, db_mod):
        sql = "SELECT E'a\\nb\\\\c';\nSELECT 1;\n"
        assert db_mod._get_disallowed_psql_meta_command(sql) is None

    def test_token_start_tracking_stays_linear(self, db_mod):
        import time

        def timed(size, runs=9):
            sql = "SELECT " + ("a" * size) + ("$" * size) + ";\n\\! touch /tmp/x\n"
            best = float("inf")
            for _ in range(runs):
                t0 = time.perf_counter()
                assert db_mod._get_disallowed_psql_meta_command(sql) is not None
                best = min(best, time.perf_counter() - t0)
            return best

        timed(2000)
        small, large = timed(10_000), timed(40_000)
        assert large < small * 8, (
            f"{small=:.6f} {large=:.6f} — 4x the input cost {large / small:.1f}x the "
            f"time; linear predicts ~4x, quadratic ~16x"
        )


class TestDumpSqlScannerStreaming:
    def test_scanner_state_survives_line_boundaries(self, db_mod):
        cases = [
            ("/* multi\n line \\! comment */\nSELECT 1;\n", False),
            ("SELECT $$ body\nwith \\! inside\n$$;\n", False),
            ("SELECT 'multi\nline \\! literal';\n", False),
            ('CREATE TABLE "multi\nline \\! ident" ();\n', False),
            ("COPY t FROM stdin;\n\\! not-a-command\n\\.\nSELECT 1;\n", False),
            ("/* open\ncomment */\n\\! after\n", True),
            ("SELECT $$a\nb$$;\n\\i /etc/passwd\n", True),
            ("SELECT 'a\nb';\n\\connect evil\n", True),
        ]
        for sql, expect_hit in cases:
            got = db_mod._get_disallowed_psql_meta_command(sql)
            assert (got is not None) is expect_hit, (sql, got)

    def test_feeding_line_by_line_matches_whole_string(self, db_mod):
        sql = (
            "-- header\nCOPY t FROM stdin;\n1\tx\\y\n\\.\n"
            "CREATE FUNCTION f() AS $b$ SELECT '\\!'; $b$ LANGUAGE sql;\n"
            "SELECT 1;\n\\gexec\n"
        )
        whole = db_mod._get_disallowed_psql_meta_command(sql)
        scanner = db_mod._PsqlSqlScanner()
        streamed = None
        for line in db_mod._iter_physical_lines(sql):
            streamed = scanner.feed(line)
            if streamed is not None:
                break
        assert whole == streamed
        assert whole is not None and whole[1] == "\\gexec"

    def test_never_slurps_the_file(self, db_mod, tmp_path):
        p = tmp_path / "dump.sql"
        p.write_text("SELECT 1;\n" * 50_000, encoding="latin-1")
        real_open = type(p).open

        class NoSlurp:
            def __init__(self, fh):
                self._fh = fh

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return self._fh.__exit__(*exc)

            def __iter__(self):
                return iter(self._fh)

            def readline(self, *a, **kw):
                limit = a[0] if a else kw.get("size")
                assert limit is not None and limit > 0, (
                    "_refuse_psql_meta_commands must bound each readline, else a "
                    "newline-free dump is slurped one 'line' at a time"
                )
                return self._fh.readline(*a, **kw)

            def read(self, *a, **kw):
                raise AssertionError(
                    "_refuse_psql_meta_commands must stream, not read() the dump"
                )

        def spy_open(self, *a, **kw):
            return NoSlurp(real_open(self, *a, **kw))

        with patch.object(type(p), "open", spy_open):
            db_mod._refuse_psql_meta_commands(str(p))

    def test_peak_memory_is_independent_of_dump_size(self, db_mod, tmp_path):
        import tracemalloc

        def peak_for(n_lines):
            p = tmp_path / f"dump_{n_lines}.sql"
            p.write_text("SELECT 1;\n" * n_lines, encoding="latin-1")
            tracemalloc.start()
            db_mod._refuse_psql_meta_commands(str(p))
            _cur, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            return peak

        small, large = peak_for(25_000), peak_for(100_000)
        assert large < small * 2, (small, large)

    def test_iter_physical_lines_splits_only_on_newline(self, db_mod):
        text = "a\x0bb\x85c d\ne\n"
        assert list(db_mod._iter_physical_lines(text)) == ["a\x0bb\x85c d\n", "e\n"]


class TestTheReportedLineNumber:
    @staticmethod
    def _expected_line(sql):
        return sql[: sql.index("\\!")].count("\n") + 1

    @pytest.mark.parametrize(
        ("label", "sql"),
        [
            ("first line", "\\! id\n"),
            ("second line", "SELECT 1;\n\\! id\n"),
            ("after a line comment", "SELECT 1; -- c\n\\! id\n"),
            ("after a block comment", "SELECT 1; /* c */\n\\! id\n"),
            ("after a multi-line block comment", "/* a\n   b\n   c */\n\\! id\n"),
            ("after a string literal", "SELECT 'x';\n\\! id\n"),
            ("after a multi-line string literal", "SELECT 'a\nb\nc';\n\\! id\n"),
            ("after an escape string literal", "SELECT E'x';\n\\! id\n"),
            ("after a dollar body", "SELECT $$b$$;\n\\! id\n"),
            ("after a multi-line dollar body", "SELECT $$a\nb$$;\n\\! id\n"),
            ("after a tagged dollar body", "SELECT $t$a\nb$t$;\n\\! id\n"),
            ("after a quoted identifier", 'SELECT "col";\n\\! id\n'),
            ("string literal closing at end of line", "SELECT 'x'\n\\! id\n"),
            ("dollar body closing at end of line", "SELECT $$b$$\n\\! id\n"),
            ("tagged dollar closing at end of line", "SELECT $t$b$t$\n\\! id\n"),
            ("quoted identifier closing at end of line", 'SELECT "c"\n\\! id\n'),
            ("block comment closing at end of line", "SELECT 1 /* c */\n\\! id\n"),
            ("after a COPY block", "COPY t FROM stdin;\n1\n2\n\\.\n\\! id\n"),
            ("deep in the file", "SELECT 1;\n" * 40 + "\\! id\n"),
        ],
    )
    def test_the_refusal_names_the_line_the_command_is_on(self, db_mod, label, sql):
        found = db_mod._get_disallowed_psql_meta_command(sql)
        assert found is not None, f"{label}: the command was not flagged at all"
        assert found[0] == self._expected_line(sql), (
            f"{label}: refused at line {found[0]}, but the command is on line "
            f"{self._expected_line(sql)}"
        )


class TestTheScannerAlwaysTerminates:
    PATHOLOGICAL = [
        "",
        "\\",
        "\\\n",
        "SELECT 'unterminated",
        "SELECT $$unterminated",
        "SELECT $tag$unterminated",
        "/* unterminated",
        'SELECT "unterminated',
        "SELECT E'unterminated",
        "COPY t FROM stdin;\n1\n",
        "--",
        "-" * 5000,
        "$" * 5000,
        "\\" * 5000,
        "'" * 5000,
        '"' * 5000,
        "$$" * 2500,
        "/*" * 2500,
        "\\restrict",
        "\\restrict abc123",
        "\\.",
        "\\.\n",
        "\\unrestrict abc123",
        "\\unrestrict abc123\n",
        "\\restrict abc123\n\\unrestrict abc123",
        "SELECT 1;" + "\n" * 5000,
    ]

    @staticmethod
    @pytest.fixture(scope="class")
    def scanned(db_mod):
        import threading

        results = []

        def run():
            results.extend(
                (sql, db_mod._get_disallowed_psql_meta_command(sql))
                for sql in TestTheScannerAlwaysTerminates.PATHOLOGICAL
            )

        worker = threading.Thread(target=run, daemon=True)
        worker.start()
        worker.join(timeout=30)
        return results if not worker.is_alive() else None

    def test_every_pathological_input_returns(self, scanned):
        assert scanned is not None, (
            "the scanner did not finish the pathological corpus within 30s — its "
            "main loop stopped advancing on some input, which on a real restore "
            "hangs the worker on attacker-supplied content"
        )
        assert len(scanned) == len(self.PATHOLOGICAL)

    def test_the_corpus_is_not_trivially_empty(self, scanned):
        assert scanned is not None, "corpus did not finish; see the sibling test"
        assert [sql for sql, found in scanned if found is not None], (
            "no pathological input was flagged; the corpus is inert"
        )


class TestTheBoundaryIsAContract:
    """What this scanner accepts, stated so it is not re-found as a bug.

    Its property is "psql will not be made to run a command", not "this dump
    is safe". A restore executes the dump's SQL as the role that connects, so
    every statement below is accepted here and will run -- and on a superuser
    role, measured 2026-09-21, `COPY ... FROM PROGRAM` puts the output of a
    shell command into a table through the exact command the zip restore path
    uses.

    These assertions are deliberately the uncomfortable direction. Filtering
    these statements one at a time would make the module's name truer without
    making it true, and would leave the next reader believing a restore of an
    untrusted backup is safe. What makes it safe is a non-superuser restore
    role; `doc/architecture/deployment.md` says so, and this pins the code's
    half of that division.
    """

    SERVER_SIDE = [
        "COPY t FROM PROGRAM 'id';\n",
        "CREATE FUNCTION f() RETURNS void AS $$ pass $$ LANGUAGE plpython3u;\n",
        "ALTER SYSTEM SET log_directory = '/tmp';\n",
        "CREATE EXTENSION IF NOT EXISTS plpython3u;\n",
        "DROP SCHEMA public CASCADE;\n",
    ]

    @pytest.mark.parametrize("sql", SERVER_SIDE)
    def test_it_accepts_sql_that_runs_with_the_role_s_privileges(self, db_mod, sql):
        assert db_mod._get_disallowed_psql_meta_command(sql) is None, (
            "this scanner refuses psql meta-commands, not SQL. If it has "
            "started refusing this, say so in its docstring and in "
            "deployment.md -- the division of responsibility moved"
        )

    def test_the_client_side_vector_it_does_refuse_is_still_refused(self, db_mod):
        """The pin above is only worth having while the real guard holds."""
        assert db_mod._get_disallowed_psql_meta_command("\\! id\n") is not None

    def test_the_two_halves_are_not_the_same_question(self, db_mod):
        """`COPY ... FROM PROGRAM` and `\\copy ... from program` differ by one
        character and by which process runs the program."""
        assert (
            db_mod._get_disallowed_psql_meta_command("COPY t FROM PROGRAM 'id';\n")
            is None
        )
        assert (
            db_mod._get_disallowed_psql_meta_command("\\copy t from program 'id'\n")
            is not None
        )
