import pytest

from odoo.service.db._dump_scanner import _get_disallowed_psql_meta_command

from .conftest import requires_pg, requires_psql

ATTACKS = {
    "plain-bang": "\\! touch {C}\n",
    "bang-after-semicolon": "SELECT 1; \\! touch {C}\n",
    "restrict-blockcomment-desync": ("\\restrict /*\n\\unrestrict /*\n\\! touch {C}\n"),
    "restrict-dollarquote-desync": ("\\restrict $$\n\\unrestrict $$\n\\! touch {C}\n"),
    "restrict-backtick": "\\restrict `touch {C}`\n",
    "unrestrict-backtick": "\\unrestrict `touch {C}`\n",
    "restrict-then-bang": "\\restrict k1 \\! touch {C}\n",
    # Every one of these is a lexer state the scanner has to leave correctly.
    # Staying inside a string or a comment one character too long is what turns
    # a payload on the next line into content it never scans, so each pairs a
    # construct with a `\!` immediately after the point psql considers it over.
    "bang-after-plain-string-ending-in-backslash": "SELECT 'a\\';\n\\! touch {C}\n",
    "bang-after-escape-string": "SELECT E'x';\n\\! touch {C}\n",
    "bang-after-escape-string-with-escaped-backslash": (
        "SELECT E'a\\\\';\n\\! touch {C}\n"
    ),
    "bang-after-doubled-quote": "SELECT 'a''b';\n\\! touch {C}\n",
    "bang-after-semicolon-inside-string": "SELECT 'a;b';\n\\! touch {C}\n",
    "bang-after-quote-inside-quoted-identifier": 'SELECT "a\'b";\n\\! touch {C}\n',
    "bang-after-unicode-escape-string": "SELECT U&'a\\0041';\n\\! touch {C}\n",
    "bang-after-nested-block-comment": "/* a /* b */ */\nSELECT 1;\n\\! touch {C}\n",
    "bang-after-tagged-dollar-quote": "SELECT $t$ x $t$;\n\\! touch {C}\n",
    "bang-after-dollar-inside-identifier": "SELECT a$b;\n\\! touch {C}\n",
    # A COPY that never starts. If the scanner entered copy-data mode from a
    # mention psql treats as text, everything after it goes unscanned.
    "bang-after-copy-named-in-a-string": (
        "SELECT 'COPY t FROM stdin;';\n\\! touch {C}\n"
    ),
    "bang-after-copy-named-in-a-comment": "-- COPY t FROM stdin;\n\\! touch {C}\n",
    "bang-after-crlf-statement": "SELECT 1;\r\n\\! touch {C}\n",
    "bang-without-trailing-newline": "SELECT 1;\n\\! touch {C}",
    # `standard_conforming_strings=off` makes the unprefixed backslash escape
    # the closing quote, so this whole string is one token to real psql and
    # the `\!` after it is a live command -- but a scanner that always
    # assumes `on` reads the escaped quote as closing the string early and
    # the real closing quote as opening a second, never-closed one, going
    # blind to everything after it.
    # A dollar-quote tag PostgreSQL accepts and an ASCII-only tag pattern does
    # not. The body then gets scanned as SQL, the apostrophe in it opens a
    # string that never closes, and everything after goes unread -- while psql
    # closes the tag and runs what follows.
    "bang-after-nonascii-dollar-tag": "SELECT $caf\u00e9$ it's $caf\u00e9$;\n\\! touch {C}\n",
    # `SET` is not the only way to reach the setting. The server reports a
    # `set_config` change and psql's lexer follows it, so the string on the
    # next line closes for the scanner and stays open for psql.
    "bang-after-conforming-strings-off-via-set_config": (
        "SELECT set_config('standard_conforming_strings','off',false);\n"
        "SELECT 'a\\'b';\n\\! touch {C}\n"
    ),
    "bang-after-plain-string-desynced-by-conforming-strings-off": (
        "SET standard_conforming_strings = off;\nSELECT 'a\\'b';\n\\! touch {C}\n"
    ),
}

BENIGN = {
    "setting-in-function": "CREATE FUNCTION pg_temp.scanner_literal() RETURNS text LANGUAGE sql AS $$ SELECT 'standard_conforming_strings = off' $$;\n",
    "inside-string": "SELECT '\\! touch {C}';\n",
    "inside-dollar-body": "SELECT $$\\! touch {C}$$;\n",
    "inside-line-comment": "-- \\! touch {C}\nSELECT 1;\n",
    "inside-block-comment": "/* \\! touch {C} */\nSELECT 1;\n",
    "in-copy-data": (
        "CREATE TEMP TABLE ct (a text);\nCOPY ct (a) FROM stdin;\n\\! touch {C}\n\\.\n"
    ),
    # The other half of the escape-string pair above, and the reason the
    # scanner needs `single_quote_escaped` at all: `'a\'` CLOSES, so the next
    # line is a command, while `E'a\'` does NOT -- the backslash escapes the
    # quote and psql reads to EOF looking for the end, then refuses the file.
    # A scanner that treated both alike would either miss a real payload or
    # reject legitimate dumps, and only real psql settles which is which.
    "after-unterminated-escape-string": "SELECT E'a\\';\n\\! touch {C}\n",
    "after-unclosed-block-comment": "/* a\nSELECT 1;\n\\! touch {C}\n",
}

LEGIT = {
    "restrict-pair": "\\restrict abc123\nSELECT 1;\n\\unrestrict abc123\n",
    # The fix for the tag above must not be "refuse every tag it cannot read".
    "nonascii-dollar-quoted-body": "SELECT $caf\u00e9$ it's fine $caf\u00e9$;\n",
    "copy-block-with-null-marker": (
        "CREATE TEMP TABLE ct (a text);\n"
        "COPY ct (a) FROM stdin;\n\\N\nplain\n\\.\nSELECT 1;\n"
    ),
}


def _write(tmp_path, name, template, canary):
    # UTF-8 on disk, which is what a dump is and what psql reads it as; the
    # scanner reads the same bytes as latin-1, exactly as production does, so
    # a multi-byte character reaches it as several characters each >= \x80.
    # Every ASCII case is byte-identical either way.
    path = tmp_path / f"{name}.sql"
    path.write_text(template.format(C=canary), encoding="utf-8")
    return path


@requires_pg
@requires_psql
class TestScannerAgreesWithPsql:
    @pytest.mark.parametrize("name", sorted(ATTACKS))
    def test_anything_psql_executes_is_rejected(self, name, tmp_path, run_psql):
        canary = tmp_path / f"canary_{name}"
        path = _write(tmp_path, name, ATTACKS[name], canary)
        rejected = _get_disallowed_psql_meta_command(path.read_text("latin-1"))
        run_psql(path)
        if canary.exists():
            assert rejected is not None, (
                f"BYPASS: psql executed the payload {name!r} and the scanner "
                f"reported the file as safe. A restore of this archive would "
                f"run arbitrary shell commands as the Odoo service account."
            )

    def test_the_canary_mechanism_is_live(self, tmp_path, run_psql):
        canary = tmp_path / "canary_live"
        path = _write(tmp_path, "live", ATTACKS["plain-bang"], canary)
        run_psql(path)
        assert canary.exists(), (
            "psql did not execute \\!, so the differential above proves nothing "
            "(check psql flags, permissions, or a restricted build)"
        )

    @pytest.mark.parametrize("name", sorted(BENIGN))
    def test_data_and_text_are_not_executed_by_either(self, name, tmp_path, run_psql):
        canary = tmp_path / f"canary_{name}"
        path = _write(tmp_path, name, BENIGN[name], canary)
        rejected = _get_disallowed_psql_meta_command(path.read_text("latin-1"))
        run_psql(path)
        assert not canary.exists(), f"payload {name!r} is not benign after all"
        assert rejected is None, (
            f"{name!r} is content psql treats as data/text, but the scanner "
            f"flags it -- a legitimate dump containing this would be refused"
        )

    @pytest.mark.parametrize("name", sorted(LEGIT))
    def test_real_dump_shapes_are_accepted_and_replay_cleanly(
        self, name, tmp_path, run_psql
    ):
        path = _write(tmp_path, name, LEGIT[name], tmp_path / "unused")
        assert _get_disallowed_psql_meta_command(path.read_text("latin-1")) is None, (
            f"the scanner refuses {name!r}, a shape real pg_dump output carries"
        )
        result = run_psql(path)
        assert result.returncode == 0, (
            f"{name!r} does not replay cleanly, so it is not a valid model of "
            f"real dump content: {result.stderr.strip()[:200]}"
        )
