import contextlib
import threading
import unittest
from decimal import Decimal
from typing import Any

from psycopg.types.json import Jsonb

from odoo.db.bulk import (
    _JSON_OIDS,
    _MAX_BIND_PARAMS,
    _NUMERIC_OID,
    _TEXT_OID,
    _BulkAccessMixin,
    _coerce_rows,
    _get_table_identifier,
    _prepare_copy_statement,
)


class TestCopyFromValidation(unittest.TestCase):
    def setUp(self):
        self.bulk: Any = _BulkAccessMixin()

    def test_empty_columns_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.copy_from("t", [], [(1,)])
        self.assertIn("non-empty", str(ctx.exception))

    def test_unknown_on_error_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.copy_from("t", ["a"], [(1,)], on_error="drop table")
        self.assertIn("invalid on_error", str(ctx.exception))

    def test_on_error_with_binary_is_rejected(self):
        with self.assertRaises(ValueError):
            self.bulk.copy_from("t", ["a"], [(1,)], on_error="ignore", binary=True)

    def test_on_error_ignore_with_returning_ids_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.copy_from(
                "t", ["a"], [(1,)], on_error="ignore", returning_ids=True
            )
        self.assertIn("returning_ids", str(ctx.exception))

    def test_returning_ids_with_id_already_in_columns_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.copy_from("t", ["id", "a"], [(1, 2)], returning_ids=True)
        self.assertIn("'id'", str(ctx.exception))

    def test_returning_ids_without_id_in_columns_is_accepted_by_the_whitelist(self):
        with self.assertRaises(Exception) as ctx:
            self.bulk.copy_from("t", ["a"], [(1,)], returning_ids=True)
        self.assertNotIsInstance(ctx.exception, ValueError)

    def test_on_error_stop_is_accepted_by_the_whitelist(self):
        with self.assertRaises(Exception) as ctx:
            self.bulk.copy_from("t", ["a"], [(1,)], on_error="stop")
        self.assertNotIsInstance(ctx.exception, ValueError)


class _FakeCopyBlock:
    def __init__(self):
        self.rows: list = []

    def set_types(self, oids):
        pass

    def write_row(self, row):
        self.rows.append(row)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeObj:
    def copy(self, stmt):
        return _FakeCopyBlock()


class _FakeCursorForCopyMetrics(_BulkAccessMixin):
    def __init__(self):
        self._obj = _FakeObj()
        self._thread = threading.current_thread()
        self.statement_done_calls: list = []

    def _before_statement(self):
        pass

    @property
    def in_pipeline(self):
        return False

    def _statement_done(
        self,
        delay,
        *,
        counts,
        query,
        params=None,
        count=1,
        label="query",
        hooks=None,
        start=0.0,
        debug=False,
    ):
        self.statement_done_calls.append(count)

    def _statement_failed(self, *args, **kwargs):
        return False

    def _record_sql_log(self, query_type, table, delay):
        pass


class TestCopyFromMetrics(unittest.TestCase):
    def test_reports_the_actual_row_count_not_a_fixed_one(self):
        cursor = _FakeCursorForCopyMetrics()
        cursor.copy_from("t", ["a"], [(i,) for i in range(5000)])  # type: ignore[misc]
        self.assertEqual(cursor.statement_done_calls, [5000])

    def test_an_empty_iterator_issues_no_statement_to_report(self):
        cursor = _FakeCursorForCopyMetrics()
        cursor.copy_from("t", ["a"], iter(()))  # type: ignore[misc]
        self.assertEqual(
            cursor.statement_done_calls,
            [],
            "an empty iterator must not reach the server, so there is no "
            "statement to record; this asserted a recorded count of 0 while "
            "the COPY was still being issued",
        )

    def test_a_generator_keeps_the_row_that_was_peeled_to_test_it(self):
        cursor = _FakeCursorForCopyMetrics()
        cursor.copy_from("t", ["a"], iter([(1,), (2,), (3,)]))  # type: ignore[misc]
        self.assertEqual(cursor.statement_done_calls, [3])


class _RejectingCopyBlock(_FakeCopyBlock):
    def write_row(self, row):
        raise TypeError("psycopg could not dump the row")


class _FakeObjWithBlock(_FakeObj):
    def __init__(self, block):
        self.block = block

    def copy(self, stmt):
        return self.block


class _FakeCursorForBinaryCopy(_FakeCursorForCopyMetrics):
    def __init__(self, block):
        super().__init__()
        self._obj = _FakeObjWithBlock(block)
        self._cnx = None

    def _get_column_type_oids(self, table, columns):
        return [23] * len(columns)

    def _is_binary_copy_worthwhile(self, oids):
        return True


class TestTheBinaryTypeNoteNamesOnlyTheEncoder(unittest.TestCase):
    def test_a_row_psycopg_refuses_to_encode_gets_the_note(self):
        cursor = _FakeCursorForBinaryCopy(_RejectingCopyBlock())
        with self.assertRaises(TypeError) as ctx:
            cursor.copy_from("t", ["a"], [(1,)], binary=True)  # type: ignore[misc]
        self.assertTrue(any("binary=True" in note for note in ctx.exception.__notes__))

    def test_a_failure_in_the_callers_own_row_source_does_not(self):
        cursor = _FakeCursorForBinaryCopy(_FakeCopyBlock())

        def rows():
            yield (1,)
            raise KeyError("the caller's generator")

        with self.assertRaises(KeyError) as ctx:
            cursor.copy_from("t", ["a"], rows(), binary=True)  # type: ignore[misc]
        self.assertIsNone(
            getattr(ctx.exception, "__notes__", None),
            "the note explains psycopg's client-side encoding; a KeyError "
            "raised by the caller's own generator has nothing to do with it "
            "and used to get the note anyway",
        )


class _FakeCursorForExecuteValues(_BulkAccessMixin):
    def __init__(self, fail_on_statement=None):
        self._obj = None
        self.executed: list = []
        self.marked: list = []
        self.pipeline_blocks: list = []
        self._fail_on_statement = fail_on_statement

    def _before_statement(self):
        pass

    def execute(self, query, params=None, log_exceptions=True):
        self.executed.append(query)
        if len(self.executed) == self._fail_on_statement:
            exc = RuntimeError("server rejected the statement")
            self.marked.append(exc)
            raise exc

    def fetchall(self):
        return [(len(self.executed),)]

    @contextlib.contextmanager
    def pipeline(self, log_exceptions=True, query=None):
        self.pipeline_blocks.append((log_exceptions, query))
        yield


class TestExecuteValuesReachesTheSeamThroughItsEntryPoints(unittest.TestCase):
    def test_every_page_is_a_plain_execute(self):
        cursor = _FakeCursorForExecuteValues()
        cursor.execute_values(  # type: ignore[misc]
            "INSERT INTO t VALUES %s", [(i,) for i in range(250)], page_size=100
        )
        self.assertEqual(len(cursor.executed), 3)
        self.assertEqual(
            cursor.pipeline_blocks,
            [(True, "INSERT INTO t VALUES %s")],
            "a multi-page write opens one pipeline block that keeps the "
            "caller's log flag and names the caller's template",
        )

    def test_a_failing_page_propagates_exactly_what_execute_raised(self):
        cursor = _FakeCursorForExecuteValues(fail_on_statement=2)
        with self.assertRaises(RuntimeError) as ctx:
            cursor.execute_values(  # type: ignore[misc]
                "INSERT INTO t VALUES %s", [(i,) for i in range(250)], page_size=100
            )
        self.assertIs(ctx.exception, cursor.marked[0])
        self.assertEqual(len(cursor.executed), 2, "the remaining pages are not sent")

    def test_a_page_never_carries_more_bind_parameters_than_the_wire_counts(self):
        cursor = _FakeCursorForExecuteValues()
        sent: list[int] = []
        cursor.execute = lambda q, params=None, log_exceptions=True: sent.append(  # type: ignore[method-assign]
            len(params)
        )
        rows = [(i, i, i) for i in range(30000)]
        cursor.execute_values(  # type: ignore[misc]
            "INSERT INTO t VALUES %s", rows, page_size=100000
        )
        self.assertEqual(sum(sent), 90000)
        self.assertLessEqual(max(sent), _MAX_BIND_PARAMS)
        self.assertEqual(
            len(sent),
            2,
            "pages are packed to the ceiling, not to a page size derived from "
            "the widest row and applied to every page",
        )

    def test_scalar_rows_are_clamped_by_the_same_ceiling(self):
        cursor = _FakeCursorForExecuteValues()
        sent: list[int] = []
        cursor.execute = lambda q, params=None, log_exceptions=True: sent.append(  # type: ignore[method-assign]
            len(params)
        )
        cursor.execute_values(  # type: ignore[misc]
            "INSERT INTO t VALUES %s", list(range(70000)), page_size=100000
        )
        self.assertEqual((sum(sent), len(sent)), (70000, 2))
        self.assertLessEqual(max(sent), _MAX_BIND_PARAMS)

    def test_mixed_widths_pack_by_what_each_row_actually_binds(self):
        cursor = _FakeCursorForExecuteValues()
        sent: list[int] = []
        cursor.execute = lambda q, params=None, log_exceptions=True: sent.append(  # type: ignore[method-assign]
            len(params)
        )
        rows = [(1,) * 60000, (2,) * 6000, (3,)]
        cursor.execute_values("INSERT INTO t VALUES %s", rows, page_size=10)  # type: ignore[misc]
        self.assertEqual(sent, [60000, 6001])

    def test_fetch_never_pipelines(self):
        cursor = _FakeCursorForExecuteValues()
        rows = cursor.execute_values(  # type: ignore[misc]
            "INSERT INTO t VALUES %s RETURNING id",
            [(i,) for i in range(250)],
            page_size=100,
            fetch=True,
        )
        self.assertEqual(rows, [(1,), (2,), (3,)])
        self.assertEqual(cursor.pipeline_blocks, [])


class TestExecuteValuesValidation(unittest.TestCase):
    def setUp(self):
        self.bulk: Any = _BulkAccessMixin()

    def test_non_positive_page_size_is_rejected(self):
        for size in (0, -1):
            with self.subTest(page_size=size), self.assertRaises(ValueError):
                self.bulk.execute_values(
                    "INSERT INTO t VALUES %s", [(1,)], page_size=size
                )

    def test_missing_marker_is_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.execute_values("INSERT INTO t VALUES (1)", [(1,)])
        self.assertIn("got 0", str(ctx.exception))

    def test_two_markers_are_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.execute_values("INSERT INTO t VALUES %s, %s", [(1,)])
        self.assertIn("got 2", str(ctx.exception))

    def test_escaped_percent_is_not_a_marker(self):
        with self.assertRaises(ValueError) as ctx:
            self.bulk.execute_values("SELECT '100%%s' FROM t", [(1,)])
        self.assertIn("got 0", str(ctx.exception))

    def test_marker_validation_precedes_the_empty_short_circuit(self):
        with self.assertRaises(ValueError):
            self.bulk.execute_values("INSERT INTO t VALUES (1)", [])

    def test_empty_argslist_short_circuits_on_a_valid_query(self):
        self.assertIsNone(self.bulk.execute_values("INSERT INTO t VALUES %s", []))
        self.assertEqual(
            self.bulk.execute_values("INSERT INTO t VALUES %s", [], fetch=True), []
        )


class TestTypeOidConstants(unittest.TestCase):
    def test_constants_match_postgres(self):
        self.assertEqual(_TEXT_OID, 25)
        self.assertEqual(_NUMERIC_OID, 1700)


class TestTableIdentifier(unittest.TestCase):
    def _render_query(self, table):
        return _get_table_identifier(table).as_string(None)

    def test_plain_name_is_quoted(self):
        self.assertEqual(self._render_query("res_partner"), '"res_partner"')

    def test_mixed_case_is_preserved_not_folded(self):
        self.assertEqual(self._render_query("MyTable"), '"MyTable"')

    def test_schema_qualified_name_becomes_two_identifiers(self):
        self.assertEqual(self._render_query("s1.t"), '"s1"."t"')

    def test_quotes_in_a_name_cannot_break_out(self):
        self.assertEqual(self._render_query('ev"il'), '"ev""il"')


class _FractionOnly(_BulkAccessMixin):
    def _can_dump_binary(self, oids):
        return True


class TestBinaryPaysOff(unittest.TestCase):
    def setUp(self):
        self.bulk: Any = _FractionOnly()

    def _oids(self, numeric, total=20):
        return [_NUMERIC_OID] * numeric + [_TEXT_OID] * (total - numeric)

    def test_no_numeric_columns_uses_binary(self):
        self.assertTrue(self.bulk._is_binary_copy_worthwhile(self._oids(0)))

    def test_a_few_numeric_columns_still_uses_binary(self):
        for n in (1, 2, 3, 4, 5):
            with self.subTest(numeric=n):
                self.assertTrue(self.bulk._is_binary_copy_worthwhile(self._oids(n)))

    def test_numeric_heavy_rows_fall_back_to_text(self):
        for n in (6, 8, 20):
            with self.subTest(numeric=n):
                self.assertFalse(self.bulk._is_binary_copy_worthwhile(self._oids(n)))

    def test_all_numeric_falls_back_however_narrow_the_row(self):
        self.assertFalse(self.bulk._is_binary_copy_worthwhile([_NUMERIC_OID]))

    def test_an_undumpable_column_vetoes_binary_regardless_of_fraction(self):
        class _NoDumper(_BulkAccessMixin):
            def _can_dump_binary(self, oids):
                return False

        self.assertFalse(_NoDumper()._is_binary_copy_worthwhile([_TEXT_OID] * 20))  # type: ignore[misc]


class TestCopyStatement(unittest.TestCase):
    def _render_query(self, *args, **kwargs):
        return _prepare_copy_statement(*args, **kwargs).as_string(None)

    def test_plain_copy_has_no_options_clause(self):
        self.assertEqual(
            self._render_query("t", ["a", "b"], False, None),
            'COPY "t" ("a", "b") FROM STDIN',
        )

    def test_binary_adds_format_binary(self):
        self.assertEqual(
            self._render_query("t", ["a"], True, None),
            'COPY "t" ("a") FROM STDIN (FORMAT BINARY)',
        )

    def test_on_error_adds_its_clause_when_the_format_is_text(self):
        self.assertEqual(
            self._render_query("t", ["a"], False, "ignore"),
            'COPY "t" ("a") FROM STDIN (ON_ERROR ignore)',
        )

    def test_on_error_is_dropped_when_the_effective_format_is_binary(self):
        self.assertEqual(
            self._render_query("t", ["a"], True, "ignore"),
            'COPY "t" ("a") FROM STDIN (FORMAT BINARY)',
        )

    def test_the_table_is_quoted_through_table_identifier(self):
        self.assertEqual(
            self._render_query('ev"il.t', ["a"], False, None),
            'COPY "ev""il"."t" ("a") FROM STDIN',
        )

    def test_column_names_are_quoted(self):
        self.assertEqual(
            self._render_query("t", ['ev"il'], False, None),
            'COPY "t" ("ev""il") FROM STDIN',
        )


class TestCoercedRows(unittest.TestCase):
    def _json_oid(self):
        return next(iter(_JSON_OIDS))

    def test_a_row_with_no_numeric_or_json_column_passes_through_unchanged(self):
        rows = [("a", 1), ("b", 2)]
        out = list(_coerce_rows(rows, [_TEXT_OID, _TEXT_OID]))
        self.assertEqual(out, rows)
        self.assertIs(out[0], rows[0])

    def test_a_float_in_a_numeric_column_becomes_an_exact_decimal(self):
        (row,) = _coerce_rows([("a", 2.675)], [_TEXT_OID, _NUMERIC_OID])
        self.assertEqual(row[1], Decimal("2.675"))
        self.assertEqual(str(row[1]), "2.675")

    def test_a_non_float_in_a_numeric_column_is_left_alone(self):
        (row,) = _coerce_rows(
            [(Decimal("1.5"), 7, None)], [_NUMERIC_OID, _NUMERIC_OID, _NUMERIC_OID]
        )
        self.assertEqual(row, [Decimal("1.5"), 7, None])

    def test_a_str_in_a_json_column_is_wrapped_so_binary_parses_it(self):
        (row,) = _coerce_rows([('{"a": 1}',)], [self._json_oid()])
        self.assertIsInstance(row[0], Jsonb)
        self.assertEqual(row[0].obj, '{"a": 1}')

    def test_an_already_wrapped_json_value_is_left_alone(self):
        wrapped = Jsonb({"a": 1})
        (row,) = _coerce_rows([(wrapped,)], [self._json_oid()])
        self.assertIs(row[0], wrapped)

    def test_a_none_in_a_json_column_is_left_alone(self):
        (row,) = _coerce_rows([(None,)], [self._json_oid()])
        self.assertIsNone(row[0])

    def test_both_coercions_apply_in_one_row(self):
        (row,) = _coerce_rows(
            [("t", 0.1, "[]")], [_TEXT_OID, _NUMERIC_OID, self._json_oid()]
        )
        self.assertEqual(row[0], "t")
        self.assertEqual(row[1], Decimal("0.1"))
        self.assertIsInstance(row[2], Jsonb)

    def test_the_column_type_list_is_consulted_by_position(self):
        (row,) = _coerce_rows([(1.5, 1.5)], [_TEXT_OID, _NUMERIC_OID])
        self.assertIsInstance(row[0], float)
        self.assertEqual(row[1], Decimal("1.5"))

    def test_an_empty_row_source_yields_nothing(self):
        self.assertEqual(list(_coerce_rows([], [_NUMERIC_OID])), [])


if __name__ == "__main__":
    unittest.main()
