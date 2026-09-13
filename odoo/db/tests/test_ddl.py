import inspect
import unittest

from odoo.db import ddl as ddl_mod
from odoo.db.ddl import (
    _SCHEMA_CHANGING_DDL,
    _get_ddl_keyword,
    _has_schema_changing_statement,
    _inline_ddl_params,
    classify_statement,
    get_value_marker_positions,
)


def _is_rollback_to_savepoint(qs):
    return classify_statement(qs)[1]


def _classify_ddl(qs):
    return _get_ddl_keyword(qs) is not None


class TestClassifyDdl(unittest.TestCase):
    def test_keywords_detected(self):
        for kw in ("CREATE", "ALTER", "DROP", "COMMENT", "GRANT", "REVOKE", "DO"):
            self.assertTrue(_classify_ddl(f"{kw} something"), kw)

    def test_dml_not_detected(self):
        for kw in ("SELECT", "INSERT", "UPDATE", "DELETE", "WITH", "TRUNCATE"):
            self.assertFalse(_classify_ddl(f"{kw} something"), kw)


class TestSetTakesClientSideParams(unittest.TestCase):
    def test_set_is_claimed(self):
        for qs in (
            "SET statement_timeout = %s",
            "SET LOCAL work_mem = %s",
            "set local statement_timeout = %s",
            "  \n\t SET SESSION x = %s",
            " " * 70 + "SET x = %s",
        ):
            self.assertEqual(classify_statement(qs), ("SET", False), qs)

    def test_select_is_not(self):
        for qs in (
            "SELECT 1",
            "select 1",
            "  SELECT id FROM t",
            " " * 70 + "SELECT 1",
            "SE",
            "SELECT setting FROM pg_settings",
        ):
            self.assertEqual(classify_statement(qs), (None, False), qs)

    def test_set_changes_no_schema(self):
        self.assertNotIn("SET", _SCHEMA_CHANGING_DDL)
        self.assertFalse(
            _has_schema_changing_statement("SET statement_timeout = '5s'", "SET")
        )
        self.assertFalse(
            _has_schema_changing_statement("SELECT 1; SET x = 1", None),
            "a hidden SET must not drain the pool either",
        )

    def test_the_se_branch_runs_no_regex(self):
        src = inspect.getsource(classify_statement)
        branch = src[src.index('if c == "SE":') :]
        branch = branch[: branch.index("\n    if ")]
        self.assertNotIn("match(", branch, "the SE branch must stay regex-free")
        self.assertNotIn(
            "SET", ddl_mod._DDL_KEYWORDS, "SET in the keyword list is the cost"
        )

    def test_inlining_a_set_produces_runnable_sql(self):
        out = _inline_ddl_params("SET statement_timeout = %s", ("5s",), None)
        self.assertEqual(out, "SET statement_timeout = '5s'")

    def test_leading_whitespace_and_comments(self):
        self.assertTrue(_classify_ddl("\n   CREATE TABLE t (id int)"))
        self.assertTrue(_classify_ddl("-- migrate\nCREATE TABLE t (id int)"))
        self.assertTrue(_classify_ddl("/* c */ ALTER TABLE t ADD COLUMN b int"))
        self.assertFalse(_classify_ddl("   SELECT 1"))

    def test_window_boundary_matches_regex(self):
        from odoo.db.ddl import _RE_DDL

        keywords = ("CREATE", "ALTER", "DROP", "COMMENT", "GRANT", "DO", "SELECT")
        tails = (" TABLE t (id int)", " 1", " * FROM t", "")
        for pad in range(96):
            for kw in keywords:
                for tail in tails:
                    qs = " " * pad + kw + tail
                    self.assertEqual(
                        _classify_ddl(qs),
                        _RE_DDL.match(qs) is not None,
                        f"gate/regex disagree at pad={pad} kw={kw!r} tail={tail!r}",
                    )


class TestDdlKeyword(unittest.TestCase):
    def test_keyword_extraction(self):
        cases = {
            "CREATE TABLE t (x int)": "CREATE",
            "   alter table t add c int": "ALTER",
            "DROP TABLE t": "DROP",
            "COMMENT ON TABLE t IS %s": "COMMENT",
            "GRANT SELECT ON t TO r": "GRANT",
            "REVOKE SELECT ON t FROM r": "REVOKE",
            "DO $$ BEGIN END $$": "DO",
            "-- migrate\nCREATE TABLE t (x int)": "CREATE",
            "SELECT 1": None,
            "WITH a AS (SELECT 1) SELECT * FROM a": None,
        }
        for qs, expected in cases.items():
            self.assertEqual(_get_ddl_keyword(qs), expected, qs)
            self.assertIs(_classify_ddl(qs), expected is not None, qs)

    def test_schema_changing_set(self):
        self.assertEqual(
            _SCHEMA_CHANGING_DDL, frozenset({"CREATE", "ALTER", "DROP", "DO"})
        )
        for kw in ("CREATE", "ALTER", "DROP", "DO"):
            self.assertIn(kw, _SCHEMA_CHANGING_DDL)
        for kw in ("COMMENT", "GRANT", "REVOKE"):
            self.assertNotIn(kw, _SCHEMA_CHANGING_DDL)


class TestRollbackToSavepointDetection(unittest.TestCase):
    def test_rollback_to_savepoint_is_detected(self):
        for qs in (
            "ROLLBACK TO SAVEPOINT foo",
            'ROLLBACK TO SAVEPOINT "foo"',
            "ROLLBACK TO foo",
            "rollback to savepoint foo",
            "  \n ROLLBACK   TO   SAVEPOINT bar",
            "/* c */ ROLLBACK TO SAVEPOINT baz",
        ):
            self.assertTrue(_is_rollback_to_savepoint(qs), qs)

    def test_non_partial_rollbacks_are_not_detected(self):
        for qs in (
            "ROLLBACK",
            "ROLLBACK;",
            "ROLLBACK WORK",
            "RELEASE SAVEPOINT foo",
            "SAVEPOINT foo",
            "SELECT 1",
            "UPDATE t SET x = 1",
            "-- ROLLBACK TO SAVEPOINT foo\nSELECT 1",
        ):
            self.assertFalse(_is_rollback_to_savepoint(qs), qs)

    def test_prefix_gate_short_circuits_non_ro_queries(self):
        self.assertTrue(_is_rollback_to_savepoint(" " * 40 + "ROLLBACK TO SAVEPOINT x"))
        self.assertFalse(_is_rollback_to_savepoint(" " * 40 + "SELECT 1"))


class TestDDLKeywordPrefixGate(unittest.TestCase):
    def test_prefixes_are_derived_from_keywords(self):
        from odoo.db.ddl import _COMMENT_PREFIXES, _DDL_KEYWORDS, _DDL_PREFIXES

        expected = frozenset(kw[:2] for kw in _DDL_KEYWORDS) | _COMMENT_PREFIXES
        self.assertEqual(_DDL_PREFIXES, expected)

    def test_every_keyword_prefix_admitted_by_gate(self):
        from odoo.db.ddl import _DDL_KEYWORDS, _DDL_PREFIXES

        for kw in _DDL_KEYWORDS:
            self.assertIn(
                kw[:2].upper(),
                _DDL_PREFIXES,
                f"keyword {kw!r}'s 2-char prefix is not admitted by the gate",
            )

    def test_gate_and_regex_never_disagree(self):
        from odoo.db.ddl import _DDL_KEYWORDS, _DDL_PREFIXES, _RE_DDL

        def gate(qs):
            head = qs[:64].lstrip()
            if len(head) < 2 and len(qs) > 64:
                head = qs.lstrip()
            c = head[:2].upper()
            return c in _DDL_PREFIXES and _RE_DDL.match(qs) is not None

        def regex(qs):
            return _RE_DDL.match(qs) is not None

        samples = []
        for kw in _DDL_KEYWORDS:
            samples += [
                f"{kw} TABLE x (c int)",
                f"  {kw} foo",
                f"\n\n\t{kw} foo",
                f"-- lead\n{kw} foo",
                f"/* lead */ {kw} foo",
                kw.lower() + " foo",
                " " * 62 + f"{kw} foo",
                " " * 63 + f"{kw} foo",
                " " * 64 + f"{kw} foo",
                " " * 80 + f"{kw} foo",
            ]
        samples += [
            "SELECT 1",
            "INSERT INTO t VALUES (1)",
            "UPDATE t SET x = 1",
            "DELETE FROM t",
            "WITH a AS (SELECT 1) SELECT * FROM a",
        ]
        for s in samples:
            self.assertEqual(
                gate(s),
                regex(s),
                f"prefix gate and regex disagree on {s!r} — derivation drifted",
            )


class TestRollbackPrefixGate(unittest.TestCase):
    def test_prefixes_are_hoisted_not_rebuilt_per_call(self):
        import odoo.db.ddl as ddl_mod

        self.assertIsInstance(
            ddl_mod._ROLLBACK_PREFIXES,
            frozenset,
            "the rollback prefix gate must be a module-level constant: it is "
            "consulted on every non-DDL statement, which is every statement "
            "the framework issues, so rebuilding it per call is ~70ns of pure "
            "waste on the hottest path in core.",
        )
        self.assertNotIn(
            "_COMMENT_PREFIXES)",
            inspect.getsource(ddl_mod.classify_statement),
            "classify_statement rebuilds a prefix container per call again; "
            "use the hoisted _ROLLBACK_PREFIXES / _DDL_PREFIXES.",
        )

    def test_prefixes_are_derived_from_the_same_sources_as_the_ddl_gate(self):
        from odoo.db.ddl import _COMMENT_PREFIXES, _ROLLBACK_PREFIXES

        self.assertEqual(_ROLLBACK_PREFIXES, frozenset(("RO",)) | _COMMENT_PREFIXES)

    def test_gate_and_regex_never_disagree(self):
        from odoo.db.ddl import _RE_ROLLBACK_TO_SAVEPOINT, _ROLLBACK_PREFIXES

        def gate(qs):
            head = qs[:32].lstrip()
            if len(head) < 2 and len(qs) > 32:
                head = qs.lstrip()
            return (
                head[:2].upper() in _ROLLBACK_PREFIXES
                and _RE_ROLLBACK_TO_SAVEPOINT.match(qs) is not None
            )

        samples = [
            'ROLLBACK TO SAVEPOINT "sp1"',
            "ROLLBACK TO sp1",
            "rollback to savepoint sp",
            "  ROLLBACK  TO  SAVEPOINT x",
            "-- lead\nROLLBACK TO x",
            "/* lead */ ROLLBACK TO x",
            " " * 30 + "ROLLBACK TO x",
            " " * 32 + "ROLLBACK TO x",
            " " * 40 + "ROLLBACK TO x",
            "ROLLBACK",
            "RELEASE SAVEPOINT sp1",
            "SELECT 1",
            "",
        ]
        for qs in samples:
            self.assertEqual(
                gate(qs),
                _RE_ROLLBACK_TO_SAVEPOINT.match(qs) is not None,
                f"prefix gate and regex disagree on {qs!r} — derivation drifted",
            )


class TestInlineDdlParams(unittest.TestCase):
    def test_positional_inlines_and_quotes(self):
        self.assertEqual(_inline_ddl_params("DEFAULT %s", (7,), None), "DEFAULT 7")
        self.assertEqual(
            _inline_ddl_params("c = %s", ("o'reilly",), None), "c = 'o''reilly'"
        )

    def test_named_dict_params(self):
        self.assertEqual(_inline_ddl_params("a = %(x)s", {"x": "v"}, None), "a = 'v'")

    def test_named_dict_missing_key_raises_valueerror(self):
        with self.assertRaises(ValueError) as cm:
            _inline_ddl_params("DEFAULT %(naem)s", {"name": 1}, None)
        self.assertIn("naem", str(cm.exception))

    def test_named_dict_unused_key_is_lenient(self):
        self.assertEqual(
            _inline_ddl_params("a = %(x)s", {"x": "v", "unused": 9}, None), "a = 'v'"
        )

    def test_named_dict_missing_with_literal_percent(self):
        with self.assertRaises(ValueError):
            _inline_ddl_params("'100%%' DEFAULT %(v)s", {}, None)
        self.assertEqual(
            _inline_ddl_params("'100%%' = %(v)s", {"v": 1}, None), "'100%' = 1"
        )

    def test_literal_percent_is_unescaped_around_marker(self):
        self.assertEqual(
            _inline_ddl_params("IS '50%% done' DEFAULT %s", ("v",), None),
            "IS '50% done' DEFAULT 'v'",
        )

    def test_double_percent_only_no_marker(self):
        self.assertEqual(
            _inline_ddl_params("COMMENT IS '100%% sure'", (), None),
            "COMMENT IS '100% sure'",
        )

    def test_marker_count_mismatch_raises(self):
        with self.assertRaises(ValueError):
            _inline_ddl_params("%s %s", ("only-one",), None)
        with self.assertRaises(ValueError):
            _inline_ddl_params("DEFAULT %s", (1, 2), None)

    def test_multiple_positional_in_order(self):
        self.assertEqual(
            _inline_ddl_params("(%s, %s, %s)", (1, 2, 3), None), "(1, 2, 3)"
        )

    def test_literal_percent_s_inside_a_string_does_not_corrupt_positional(self):
        with self.assertRaises(ValueError):
            _inline_ddl_params(
                "COMMENT ON COLUMN t.c IS 'use %s as format' -- %s",
                ("A", "B"),
                None,
            )
        self.assertEqual(
            _inline_ddl_params(
                "COMMENT ON COLUMN t.c IS 'use %s as format' DEFAULT %s -- trailing",
                ("A",),
                None,
            ),
            "COMMENT ON COLUMN t.c IS 'use %s as format' DEFAULT 'A' -- trailing",
        )

    def test_literal_named_marker_inside_a_string_or_comment_is_left_alone(self):
        self.assertEqual(
            _inline_ddl_params(
                "IS 'use %(x)s literally' /* also %(x)s */ DEFAULT %(x)s",
                {"x": 42},
                None,
            ),
            "IS 'use %(x)s literally' /* also %(x)s */ DEFAULT 42",
        )

    def test_named_marker_referenced_only_inside_a_string_is_not_required(self):
        self.assertEqual(
            _inline_ddl_params("IS 'contains %(x)s literally'", {}, None),
            "IS 'contains %(x)s literally'",
        )


class TestChangesSchema(unittest.TestCase):
    def _check(self, qs):
        return _has_schema_changing_statement(qs, _get_ddl_keyword(qs))

    def test_single_statement_schema_ddl(self):
        for qs in (
            "CREATE TABLE t (id int)",
            "ALTER TABLE t ADD COLUMN c int",
            "DROP TABLE t",
            "DO $$ BEGIN END $$",
            "  -- note\n  ALTER TABLE t ALTER COLUMN c TYPE text",
        ):
            with self.subTest(qs=qs):
                self.assertTrue(self._check(qs))

    def test_single_statement_non_schema_ddl_and_dml(self):
        for qs in (
            "SELECT 1",
            "UPDATE t SET a = 1",
            "COMMENT ON TABLE t IS 'x'",
            "GRANT SELECT ON t TO PUBLIC",
            "REVOKE ALL ON t FROM PUBLIC",
            "TRUNCATE TABLE t",
        ):
            with self.subTest(qs=qs):
                self.assertFalse(self._check(qs))

    def test_ddl_hidden_behind_a_leading_non_ddl_statement(self):
        for qs in (
            "BEGIN; ALTER TABLE t ADD COLUMN c int; COMMIT",
            "SET LOCAL lock_timeout = '5s'; DROP TABLE t",
            "SELECT 1; CREATE INDEX i ON t (id)",
            "UPDATE t SET a = 1;\n  ALTER TABLE t DROP COLUMN b",
        ):
            with self.subTest(qs=qs):
                self.assertTrue(self._check(qs), qs)

    def test_multi_statement_without_schema_ddl_stays_false(self):
        for qs in (
            "SELECT 1; SELECT 2",
            "BEGIN; UPDATE t SET a = 1; COMMIT",
            "SET x = 1; COMMENT ON TABLE t IS 'y'",
        ):
            with self.subTest(qs=qs):
                self.assertFalse(self._check(qs))

    def test_leading_schema_ddl_short_circuits_before_any_scan(self):
        qs = "CREATE TABLE t (id int); COMMENT ON TABLE t IS 'x'"
        self.assertTrue(_has_schema_changing_statement(qs, "CREATE"))

    def test_over_reports_rather_than_misses(self):
        self.assertTrue(self._check("SELECT 'a; DROP TABLE t'"))

    def test_no_semicolon_never_pays_for_a_split(self):
        self.assertFalse(_has_schema_changing_statement("SELECT " + "x" * 10_000, None))

    def test_creating_a_sequence_changes_no_schema_anyone_cached(self):
        for qs in (
            'CREATE SEQUENCE "ir_sequence_12" INCREMENT BY %s START WITH %s',
            "create sequence s",
            "CREATE TEMPORARY SEQUENCE s",
            "CREATE UNLOGGED SEQUENCE s",
            "-- new sequence\nCREATE SEQUENCE s",
        ):
            with self.subTest(qs=qs):
                self.assertEqual(_get_ddl_keyword(qs), "CREATE", qs)
                self.assertFalse(self._check(qs), qs)

    def test_every_other_create_still_reports(self):
        for qs in (
            "CREATE TABLE t (id int)",
            "CREATE INDEX i ON t (a)",
            "CREATE OR REPLACE VIEW v AS SELECT 1",
            "CREATE SEQUENCES_IS_NOT_A_KEYWORD s",
        ):
            with self.subTest(qs=qs):
                self.assertTrue(self._check(qs), qs)

    def test_a_sequence_in_the_tail_is_exempt_too(self):
        self.assertFalse(self._check("SELECT 1; CREATE SEQUENCE s"))
        self.assertTrue(self._check("SELECT 1; CREATE TABLE t (id int)"))


if __name__ == "__main__":
    unittest.main()


class TestFindValueMarkers(unittest.TestCase):
    def test_basic_and_escapes(self):
        self.assertEqual(get_value_marker_positions("%s and %s"), [0, 7])
        self.assertEqual(get_value_marker_positions("LIKE 'a%%s'"), [])
        self.assertEqual(get_value_marker_positions("x %s y %% z %s"), [2, 12])
        self.assertEqual(get_value_marker_positions("%%"), [])
        self.assertEqual(get_value_marker_positions("ends %s"), [5])

    def test_a_literal_percent_s_inside_a_string_is_not_a_marker(self):
        query = "INSERT INTO t (a,b) VALUES ('has a %s inside', %s)"
        markers = get_value_marker_positions(query)
        self.assertEqual(markers, [len(query) - 3])
        self.assertEqual(query[markers[0] : markers[0] + 2], "%s")

    def test_a_literal_percent_s_inside_a_line_comment_is_not_a_marker(self):
        self.assertEqual(get_value_marker_positions("SELECT 1 -- %s\n"), [])

    def test_a_literal_percent_s_inside_a_block_comment_is_not_a_marker(self):
        query = "SELECT 1 /* %s */ %s"
        self.assertEqual(get_value_marker_positions(query), [query.rindex("%s")])

    def test_a_doubled_quote_inside_a_literal_does_not_end_it_early(self):
        query = "a = 'it''s %s' AND b = %s"
        markers = get_value_marker_positions(query)
        self.assertEqual(markers, [len(query) - 2])
