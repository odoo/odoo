"""What the two RPC entry points of ``base_import.import`` accept.

Every value exercised here reaches the server from a place the user controls
and nothing validated: ``res_model`` is a plain ``Char`` the client fills in at
``create`` time, ``fields`` is the mapping the client assembled, and ``skip`` /
``limit`` come from two free-text ``<input>`` elements in the batch panel. Each
one used to fail in its own way, and the failures split into two kinds that
want different fixes:

* **HTTP 500.** ``execute_import`` catches only ``ImportValidationError``, so a
  ``TypeError``, ``IndexError``, ``KeyError`` or ``AttributeError`` raised while
  building the parse plan escaped as a server error with a Python message.
* **Silence**, which is worse. ``skip=-1`` is not an error to Python at all:
  ``data[-1:]`` is a legal slice, so the import ran on the last row of the file
  and reported success.
"""

import unittest
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import BaseCase, TransactionCase, can_import


class ImportOptionValidation(TransactionCase):
    _CSV = b"value\nA\nB\nC\nD\n"
    _OPTS = {"has_headers": True, "quoting": '"', "separator": ",", "encoding": "utf-8"}

    def _imp(self, res_model="import.char", **vals):
        vals.setdefault("res_model", res_model)
        vals.setdefault("file", self._CSV)
        vals.setdefault("file_name", "x.csv")
        vals.setdefault("file_type", "text/csv")
        return self.env["base_import.import"].create(vals)

    def _run(self, **options):
        return self._imp().execute_import(
            ["value"], ["Value"], dict(self._OPTS, **options), dryrun=True
        )

    def _message(self, result):
        self.assertTrue(
            result.get("messages"), "expected a reported error, got %s" % result
        )
        return result["messages"][0]["message"]

    # -- limit ---------------------------------------------------------------

    def test_non_numeric_limit_is_reported_not_raised(self):
        """`num_rows > "abc"` and `limit >= len(data)` both raise TypeError."""
        self.assertIn("Batch limit", self._message(self._run(limit="abc")))

    def test_negative_limit_is_reported_not_raised(self):
        """A negative limit used to IndexError out of the row window."""
        self.assertIn("Batch limit", self._message(self._run(limit=-5)))

    def test_numeric_string_limit_is_accepted(self):
        """The batch inputs are untyped, so the client already sends a string
        for some edits; coerce rather than refuse a round trip that works."""
        options = dict(self._OPTS, limit="2")
        result = self._imp().execute_import(["value"], ["Value"], options, dryrun=True)
        self.assertFalse(result.get("messages"), result)
        self.assertEqual(len(result["ids"]), 2)

    def test_non_numeric_limit_does_not_blame_the_file(self):
        """`parse_preview` caught the TypeError with its blanket handler and
        told the user the *file* could not be read -- of a perfectly good
        file, while the actual fault was one character in an option box."""
        result = self._imp().parse_preview(dict(self._OPTS, limit="abc"))
        self.assertIn("Batch limit", result["error"])
        self.assertNotIn("could not be read", result["error"])

    def test_every_falsy_limit_means_no_limit(self):
        """`skip` unset is 0; `limit` unset is None. Folding one into the
        other, or leaving the falsy spellings alone, both go wrong.

        `_batch_window` already treats a falsy limit as "no batching" and hands
        `load` every row -- but `load` only reads **None** that way (it
        substitutes `float("inf")`); every other falsy value lands in
        `index < limit` as itself. Measured through `load` directly:

          _import_limit=None  -> 4 of 4 rows
          _import_limit=0     -> none, reported as success with nextrow=0, so
                                 the client is told the import finished
          _import_limit=False -> the same, `False < 1` being `0 < 1`
          _import_limit=""    -> TypeError: '<' not supported between
                                 instances of 'int' and 'str'  -> HTTP 500

        Resolving the disagreement in `_batch_window`'s favour is what the one
        intent this module actually states says.
        """
        for empty in (None, False, "", 0):
            with self.subTest(limit=empty):
                result = self._run(limit=empty)
                self.assertFalse(result.get("messages"), result)
                self.assertEqual(len(result["ids"]), 4)

    def test_an_absent_limit_is_left_absent(self):
        options = dict(self._OPTS)
        self.env["base_import.import"]._normalize_row_window_options(options)
        self.assertNotIn("limit", options)

    def test_an_empty_skip_is_zero(self):
        """The other half: `[""] * None` in `_record_names` raised."""
        options = dict(self._OPTS, skip=None)
        self.env["base_import.import"]._normalize_row_window_options(options)
        self.assertEqual(options["skip"], 0)

    # -- skip ----------------------------------------------------------------

    def test_negative_skip_is_refused_rather_than_silently_reversed(self):
        """The one that produced no error at all: `data[-2:]` imported the
        LAST two rows of the file and reported success.

        Reachable from the UI, not just over RPC: "Start at line" sends
        `value - 1`, and the string "0" is truthy in JavaScript.
        """
        self.assertIn("Start at line", self._message(self._run(skip=-2)))

    def test_positive_skip_still_selects_from_the_front(self):
        """Control for the test above: the fix must not disturb the real case."""
        result = self._run(skip=2)
        self.assertFalse(result.get("messages"), result)
        self.assertEqual(
            self.env["import.char"].browse(result["ids"]).mapped("value"), ["C", "D"]
        )

    def _run_named(self, **options):
        """`res.partner`, not `import.char`: the padding lives in the branch
        `execute_import` takes only when a column is mapped to `name`, and the
        test models have no such field -- so a test written against them would
        assert an empty list for the wrong reason and pass either way.
        """
        imp = self._imp("res.partner", file=b"name\nA\nB\nC\nD\n")
        return imp.execute_import(
            ["name"], ["Name"], dict(self._OPTS, **options), dryrun=True
        )

    def test_skip_past_end_of_file_does_not_allocate_per_skipped_row(self):
        """`name` is padded with one blank per skipped row so the client can
        index it by absolute file row. The padding was dense and unbounded, so
        a `skip` past the end of a four-row file allocated a list of that many
        empty strings -- 5,000,000 of them measured at 44 MiB -- to carry no
        names at all.
        """
        result = self._run_named(skip=5_000_000)
        self.assertEqual(result["ids"], [])
        self.assertEqual(result["name"], [])

    def test_skip_within_the_file_still_pads_to_absolute_rows(self):
        """Control: the padding is what makes `resultNames[error.rows.from]`
        address the right row, so it must survive for a legitimate skip."""
        self.assertEqual(self._run_named(skip=2)["name"], ["", "", "C", "D"])

    # -- the column mapping --------------------------------------------------

    def test_non_string_field_mapping_is_reported_not_raised(self):
        """Every consumer treats a mapped entry as a `'/'`-joined path and
        calls `.split` on it."""
        result = self._imp().execute_import(
            [123, "value"], ["A", "Value"], dict(self._OPTS), dryrun=True
        )
        self.assertIn("Column 1", self._message(result))

    # -- res_model -----------------------------------------------------------

    def test_unknown_res_model_is_a_user_error_not_a_key_error(self):
        for entry_point in (
            lambda imp: imp.parse_preview(dict(self._OPTS)),
            lambda imp: imp.execute_import(["value"], ["Value"], dict(self._OPTS)),
        ):
            with self.subTest(entry_point=entry_point), self.assertRaises(UserError):
                entry_point(self._imp("nope.nope"))

    def test_missing_res_model_is_a_user_error_not_a_key_error(self):
        """`res_model` is not `required`, so a record can be created without
        one and `self.env[False]` raised `KeyError: False`."""
        imp = self.env["base_import.import"].create(
            {"file": self._CSV, "file_name": "x.csv", "file_type": "text/csv"}
        )
        with self.assertRaises(UserError):
            imp.parse_preview(dict(self._OPTS))

    def test_get_fields_tree_refuses_an_unknown_model(self):
        """A public RPC entry point of its own."""
        with self.assertRaises(UserError):
            self.env["base_import.import"].get_fields_tree("nope.nope")


@unittest.skipUnless(can_import("odf"), "odfpy not installed")
class ODSCellFidelity(BaseCase):
    """The ODS reader must hand back the cells the sheet holds.

    ``BaseCase``, not a bare ``unittest.TestCase``: Odoo's loader filters by
    test tags, and an untagged ``unittest.TestCase`` in an addon matches no tag
    and is therefore never collected -- ``--test-tags
    '/test_import_export:TestODSReaderHardening'`` answers "matched no test at
    all". No database is needed, which is the whole reason the sibling class
    reached for plain unittest in the first place; ``BaseCase`` gives the tags
    without giving a cursor.
    """

    def _sheet(self, rows):
        import io

        from odf.opendocument import OpenDocumentSpreadsheet
        from odf.table import Table, TableCell, TableRow
        from odf.text import P

        from odoo.addons.base_import.models.odf_ods_reader import ODSReader

        doc = OpenDocumentSpreadsheet()
        table = Table(name="Sheet1")
        for line in rows:
            row = TableRow()
            for text, repeat in line:
                cell = TableCell()
                if repeat != 1:
                    cell.setAttribute("numbercolumnsrepeated", str(repeat))
                if text:
                    cell.addElement(P(text=text))
                row.addElement(cell)
            table.addElement(row)
        doc.spreadsheet.addElement(table)
        buf = io.BytesIO()
        doc.write(buf)
        return ODSReader(file=io.BytesIO(buf.getvalue())).get_sheet("Sheet1")

    def test_a_cell_starting_with_hash_is_data_not_a_comment(self):
        """The reader dropped it -- and dropped it *without a placeholder*, so
        every later column of that row shifted one to the left, differently per
        row. ODF has no comment-cell convention; the rule came from a
        third-party recipe this reader descends from.

        The damage is silent wrong data rather than a rejected file: below, the
        colour column would import "1" and the quantity nothing.
        """
        self.assertEqual(
            self._sheet(
                [
                    [("name", 1), ("colour", 1), ("qty", 1)],
                    [("Alice", 1), ("#FF0000", 1), ("1", 1)],
                ]
            ),
            [["name", "colour", "qty"], ["Alice", "#FF0000", "1"]],
        )

    def test_repeated_cells_at_the_end_of_a_row_are_expanded(self):
        """The repeat on the last cell of a row was ignored outright, to drop
        the "to the end of the used range" filler producers write. But that
        filler is recognisable by being *blank*, not by being last: a row
        genuinely ending in repeated values was truncated, and the file then
        failed to import on a row-width mismatch.
        """
        self.assertEqual(
            self._sheet([[("a", 1), ("b", 3)]]),
            [["a", "b", "b", "b"]],
        )

    def test_a_blank_last_cell_contributes_exactly_one_column(self):
        """The two ways a row can end blank, and why the answer is 1 for both.

        Not `repeat`: the "to the end of the used range" filler carries a count
        in the thousands, and expanding it pads every row with phantom columns
        that `_prepare_column_examples` then offers in the mapping UI.

        Not 0 either, which is what a first attempt at this did. LibreOffice
        writes an ordinary trailing empty column as a bare
        `<table:table-cell/>` with no repeat -- for `Bob,blue,2,` it emits four
        cells, the last empty (verified against a real CSV -> ODS conversion) --
        so dropping it makes that row one narrower than its header and the
        import dies on a width mismatch it should never have seen.
        """
        self.assertEqual(
            self._sheet([[("a", 1), ("b", 1), ("", 1013)]]),
            [["a", "b", ""]],
            "the used-range filler must not be expanded",
        )
        self.assertEqual(
            self._sheet(
                [[("h1", 1), ("h2", 1), ("h3", 1)], [("a", 1), ("b", 1), ("", 1)]]
            ),
            [["h1", "h2", "h3"], ["a", "b", ""]],
            "an ordinary trailing empty column must keep the row's width",
        )

    def test_repeat_count_is_still_capped(self):
        """A crafted repeat count OOM-crashes the worker; the cap is the only
        thing between the two. Asserted by nothing until now: the test that
        claimed to cover it was never collected *and* called `getSheet`, a
        method this reader has never had, so it could only ever have errored.
        """
        from odoo.addons.base_import.models.odf_ods_reader import MAX_CELL_REPEAT

        row = self._sheet([[("x", 10**8), ("", 1)]])[0]
        # +1 for the trailing blank, which is kept as exactly one column.
        self.assertEqual(len(row), MAX_CELL_REPEAT + 1)


class ParsedFileCache(TransactionCase):
    """`execute_import` re-reads the uploaded file on every batch -- the
    batches are separate RPC calls, and nothing carried the parse between them.
    Measured on a 5,000-row xlsx at limit 500, that is 8.2-8.8 s of import
    against 6.3-6.5 s once the parse is shared: a quarter of the wall time
    spent producing eleven identical row lists.
    """

    _OPTS = {"has_headers": True, "quoting": '"', "separator": ",", "encoding": "utf-8"}

    def setUp(self):
        super().setUp()
        from odoo.addons.base_import.models.base_import import PARSED_FILE_CACHE

        self.cache = PARSED_FILE_CACHE
        self.cache.clear()
        self.addCleanup(self.cache.clear)

    def _imp(self, file):
        return self.env["base_import.import"].create(
            {
                "res_model": "import.char",
                "file": file,
                "file_name": "x.csv",
                "file_type": "text/csv",
            }
        )

    def _reader_calls(self):
        model = self.env["base_import.import"]
        return patch.object(
            type(model),
            "_read_file_uncached",
            autospec=True,
            side_effect=type(model)._read_file_uncached,
        )

    def test_the_same_file_is_parsed_once(self):
        imp = self._imp(b"value\nA\nB\n")
        with self._reader_calls() as reader:
            for _ in range(3):
                imp._read_file(dict(self._OPTS))
            self.assertEqual(reader.call_count, 1)

    def test_a_new_file_on_the_same_record_is_reparsed(self):
        """The hazard a record-keyed cache would have walked into:
        ``write_date`` is the *transaction* timestamp, so two writes to
        ``file`` inside one transaction carry the same one and the second read
        would have been served the first file's rows. Keying on content is
        what makes this test pass.
        """
        imp = self._imp(b"value\nA\n")
        self.assertEqual(imp._read_file(dict(self._OPTS)), [["value"], ["A"]])
        imp.write({"file": b"value\nB\n"})
        self.assertEqual(imp._read_file(dict(self._OPTS)), [["value"], ["B"]])

    def test_options_a_reader_writes_are_replayed_on_a_hit(self):
        """The readers report back what they had to guess (encoding, separator)
        and what the workbook held (`sheets`); the client renders both. A hit
        that skipped the reader has to say the same things a miss would.
        """
        imp = self._imp("value;note\nA;caf\u00e9\n".encode("utf-8"))
        miss, hit = {"has_headers": True}, {"has_headers": True}
        imp._read_file(miss)
        imp._read_file(hit)
        self.assertEqual(hit, miss)
        self.assertEqual(hit["separator"], ";")

    def test_a_caller_cannot_corrupt_the_entry(self):
        """`parse_preview` pops the header row off the list it is handed."""
        imp = self._imp(b"value\nA\nB\n")
        first = imp._read_file(dict(self._OPTS))
        first.pop(0)
        self.assertEqual(imp._read_file(dict(self._OPTS)), [["value"], ["A"], ["B"]])

    def test_a_full_import_does_not_mutate_the_cached_rows(self):
        """The claim the whole cache rests on, asserted rather than reasoned.

        Sharing one row list between batches is only safe because every
        in-place stage works on the copies `_convert_import_data` makes
        (`list(mapper(row))`). The binary column is the sharpest case:
        `_extract_binary_filenames` blanks local-filename cells *in place*
        before `load` sees them.
        """
        import copy

        imp = self._imp(b"name,image_1920\nA,photo.png\nB,other.png\nC,third.png\n")
        imp.res_model = "res.partner"
        self.cache.clear()
        options = dict(self._OPTS)
        pristine = copy.deepcopy(imp._read_file(dict(options)))
        key = imp._parsed_file_key(dict(options))

        imp.execute_import(
            ["name", "image_1920"],
            ["name", "image"],
            dict(options, limit=2),
            dryrun=True,
        )
        imp.execute_import(
            ["name", "image_1920"],
            ["name", "image"],
            dict(options, limit=2, skip=2),
            dryrun=True,
        )
        self.assertEqual(self.cache.get(key)[0], pristine)

    def test_a_caller_cannot_corrupt_the_replayed_options(self):
        """`sheets` is a list and the reader leaves the object it built in the
        caller's `options`. Storing that reference let a caller that appended
        to its own `options["sheets"]` rewrite the entry, so every later hit
        reported a sheet the workbook does not have. Both directions are
        copied; both directions are checked here.
        """
        # Two columns, so the sniffer actually resolves (and records) a
        # separator -- a one-column file never sets one, and the assertion
        # below would pass vacuously.
        imp = self._imp(b"value;note\nA;x\n")
        first = {"has_headers": True}
        imp._read_file(first)
        self.assertEqual(first["separator"], ";")
        first.setdefault("sheets", []).append("INJECTED")
        first["separator"] = "\t"

        second = {"has_headers": True}
        imp._read_file(second)
        self.assertNotIn("INJECTED", second.get("sheets", []))
        self.assertEqual(second["separator"], ";")

    def test_the_same_bytes_under_a_different_name_are_not_shared(self):
        """`_read_file` dispatches on the name and the declared mimetype as
        well as on the content, so all three are in the key."""
        payload = b"value\nA\n"
        as_csv = self._imp(payload)
        as_xlsx = self.env["base_import.import"].create(
            {
                "res_model": "import.char",
                "file": payload,
                "file_name": "x.xlsx",
                "file_type": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            }
        )
        self.assertEqual(as_csv._read_file(dict(self._OPTS)), [["value"], ["A"]])
        # Must fail as an unreadable workbook, not quietly serve the CSV rows.
        with self.assertRaises(UserError):
            as_xlsx._read_file(dict(self._OPTS))

    def test_a_file_over_the_cell_budget_is_not_kept(self):
        """The cap is what bounds a worker's memory; above it the module
        behaves exactly as it did before."""
        from odoo.addons.base_import.models.base_import import (
            PARSED_FILE_CACHE_MAX_CELLS,
        )

        rows = PARSED_FILE_CACHE_MAX_CELLS + 1
        imp = self._imp(b"value\n" + b"A\n" * rows)
        with self._reader_calls() as reader:
            imp._read_file(dict(self._OPTS))
            imp._read_file(dict(self._OPTS))
            self.assertEqual(reader.call_count, 2)


class SpreadsheetDateColumnTyping(TransactionCase):
    """A column the reader already resolved to native `datetime.date` objects.

    `get_matching_pattern` skips date instances, so every candidate pattern matches
    vacuously over such a column and the first one is returned as if confirmed
    -- then written into `options["date_format"]` and shown to the user as the
    format their file is in.
    """

    def test_native_dates_do_not_invent_a_date_format(self):
        import datetime

        options = {"has_headers": True}
        types = self.env["base_import.import"]._extract_header_types(
            [datetime.date(2024, 1, 15), datetime.date(2024, 2, 20)], options
        )
        self.assertEqual(types, ["date", "datetime"], "the typing must not change")
        self.assertNotIn("date_format", options)

    def test_a_textual_date_column_still_sets_the_format(self):
        """Control: inference from text is the whole point of the mechanism."""
        options = {"has_headers": True}
        self.env["base_import.import"]._extract_header_types(
            ["2024-01-15", "2024-02-20"], options
        )
        self.assertEqual(options["date_format"], "%Y-%m-%d")
