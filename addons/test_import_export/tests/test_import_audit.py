"""Regression tests for the base_import correctness/security/perf audit.

Each test pins behaviour that was wrong before the audit; the docstring states
what the old behaviour was, so a future change that reintroduces it fails here
with an explanation rather than a bare assertion diff.

The crash-class tests are deliberately phrased as "this is a clean import error,
not an exception": every one of them used to escape ``execute_import`` -- which
catches only :class:`ImportValidationError` -- and surface as an HTTP 500.
"""

import contextlib
import datetime
import io
import unittest
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, can_import, new_test_user

from odoo.addons.base_import.models.base_import import (
    EXTENSION_TO_READER,
    Base_ImportImport,
    ImportValidationError,
)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
CSV_OPTS = {"quoting": '"', "separator": ",", "has_headers": True, "encoding": "utf-8"}


def make_xlsx(headers, rows, date_columns=()):
    """Build an in-memory xlsx. ``date_columns`` are 1-based column numbers
    stamped with a number format openpyxl recognises as a date (lower-case --
    'YYYY-MM-DD' is classified as *time* and would not produce a date object).
    """
    import openpyxl

    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(list(headers))
    for row in rows:
        sheet.append(list(row))
    for row_index in range(2, len(rows) + 2):
        for column in date_columns:
            sheet.cell(row=row_index, column=column).number_format = "yyyy-mm-dd"
    buf = io.BytesIO()
    book.save(buf)
    return buf.getvalue()


class ImportAuditCommon(TransactionCase):
    def _wizard(self, res_model="import.char", **vals):
        vals.setdefault("res_model", res_model)
        return self.env["base_import.import"].create(vals)

    def _csv(self, content, res_model="import.char", **vals):
        return self._wizard(
            res_model, file=content, file_name="t.csv", file_type="text/csv", **vals
        )


class TestReaderDispatch(ImportAuditCommon):
    def test_extension_dispatch_is_allow_listed(self):
        """`_read_file` used to do getattr(self, '_read_' + <filename suffix>).

        A file named 'x.file' therefore resolved to `_read_file` itself and
        recursed until the stack ran out; because every frame logged its own
        chained traceback and each one re-renders the whole __context__ chain,
        a single upload produced ~980 log records and ~240 MiB of log text,
        pinning a worker for ~60s. Unrelated ORM internals were reachable the
        same way ('x.group' -> _read_group, 'x.format' -> _read_format).
        """
        calls = []
        # Patch once, outside the loop: `self.patch` stacks for the whole test,
        # so re-patching per iteration would wrap the previous wrapper and
        # double-count.
        real = Base_ImportImport._read_file
        self.patch(
            Base_ImportImport,
            "_read_file",
            lambda s, o: (calls.append(1), real(s, o))[1],
        )
        for name in ("payload.file", "payload.group", "payload.format"):
            wizard = self._wizard(
                file=b"\x00\x01junk", file_name=name, file_type="application/x-thing"
            )
            calls.clear()
            with self.assertRaises(UserError):
                wizard._read_file({"quoting": '"'})
            self.assertEqual(len(calls), 1, f"{name} re-entered _read_file")

    def test_allow_list_covers_the_extensions_the_ui_offers(self):
        """The dropzone/button accept list and the reader table must agree."""
        self.assertEqual(
            set(EXTENSION_TO_READER),
            {"csv", "ods", "xls", "xlsm", "xlsx"},
        )

    def test_readers_return_rows_only(self):
        """Readers used to return `(file_length, rows)` with three different
        meanings for the length (`sheet.nrows` and `max_row` count blank rows,
        csv/ods count kept rows). It gated exactly one `<= 0` check and was
        discarded everywhere else, so the inconsistency only ever caused bugs.
        """
        wizard = self._csv(b"value\nx\ny\n")
        self.assertEqual(wizard._read_file(dict(CSV_OPTS)), [["value"], ["x"], ["y"]])


class TestCleanErrors(ImportAuditCommon):
    def test_header_only_file_is_mappable_not_an_internal_error(self):
        """`preview[0]` was indexed unconditionally after the header row was
        popped, so a header-only file raised IndexError, which the blanket
        handler turned into the literal text 'list index out of range' in the
        UI. The file should stay mappable with empty examples instead.
        """
        result = self._csv(b"value\n").parse_preview(dict(CSV_OPTS))
        self.assertNotIn("error", result, result.get("error"))
        self.assertEqual(result["headers"], ["value"])
        self.assertEqual(result["preview"], [[""]])
        self.assertEqual(result["num_rows"], 0)

    def test_num_rows_counts_data_rows_only(self):
        """It counted the header too, so the client's batch count
        (ceil((num_rows - skip) / limit)) was one row too high."""
        self.assertEqual(
            self._csv(b"value\na\nb\n").parse_preview(dict(CSV_OPTS))["num_rows"], 2
        )

    def test_multi_character_text_delimiter_reports_a_clean_error(self):
        """The single-character check ran *after* the separator sniffer had
        already handed `quoting` to csv.reader, so on the default path (no
        explicit separator) the user got csv's raw TypeError instead.
        """
        wizard = self._csv(b"a,b\n1,2\n")
        for options in ({"quoting": '""'}, {"quoting": '""', "separator": ","}):
            with self.assertRaises(ImportValidationError):
                wizard._read_csv(dict(options))

    def test_quoting_defaults_instead_of_raising_keyerror(self):
        """Non-UI callers (RPC, automation) that omit `quoting` used to get
        KeyError, surfaced as a misleading 'Unable to read file as csv'."""
        self.assertEqual(
            self._csv(b"a,b\n1,2\n")._read_csv({"separator": ","}),
            [["a", "b"], ["1", "2"]],
        )

    def test_unexpected_errors_are_logged_and_not_shown_verbatim(self):
        """Every exception used to be handed to the user as `str(error)` and
        logged only at debug level, so a defect in this code read as gibberish
        in the UI ("list index out of range") and left no trace in the log.
        """
        wizard = self._csv(b"value\nx\n")
        self.patch(
            type(wizard),
            "_read_file",
            lambda self, options: (_ for _ in ()).throw(AttributeError("boom")),
        )
        with self.assertLogs(
            "odoo.addons.base_import.models.base_import", level="ERROR"
        ) as logs:
            result = wizard.parse_preview(dict(CSV_OPTS))
        self.assertNotIn("boom", result["error"])
        self.assertIn("could not be read", result["error"])
        self.assertTrue(any("Unexpected error" in line for line in logs.output))

    def test_expected_errors_still_reach_the_user_verbatim(self):
        """The actionable messages must not be swallowed by the above."""
        wizard = self._csv(b"")
        result = wizard.parse_preview(dict(CSV_OPTS))
        self.assertIn("no content", result["error"])

    def test_ragged_rows_do_not_break_the_preview(self):
        """A data row narrower than the header used to raise IndexError while
        building the per-column examples."""
        result = self._csv(b"a,b,c\n1\n").parse_preview(dict(CSV_OPTS))
        self.assertNotIn("error", result, result.get("error"))
        self.assertEqual(len(result["preview"]), 3)


@unittest.skipUnless(can_import("openpyxl"), "openpyxl not available")
class TestSpreadsheetDateCells(ImportAuditCommon):
    """The xls/xlsx readers hand back native date/datetime objects. Landing one
    in a column that expects a string raised a bare AttributeError/TypeError
    that escaped execute_import as an HTTP 500.
    """

    def test_date_cell_in_a_float_column(self):
        wizard = self._wizard(
            "import.float",
            file=make_xlsx(["value"], [[datetime.date(2024, 1, 1)]], [1]),
            file_name="f.xlsx",
            file_type=XLSX_MIME,
        )
        result = wizard.execute_import(["value"], ["value"], {"has_headers": True})
        self.assertTrue(result.get("messages"), "expected a clean import error")

    def test_date_cell_in_a_multi_mapped_many2many_column(self):
        wizard = self._wizard(
            "res.partner",
            file=make_xlsx(
                ["a", "b"], [[datetime.date(2024, 1, 1), "Consulting"]], [1]
            ),
            file_name="m.xlsx",
            file_type=XLSX_MIME,
        )
        result = wizard.execute_import(
            ["category_id", "category_id"], ["a", "b"], {"has_headers": True}
        )
        self.assertIsInstance(result, dict)

    def test_date_cell_with_a_boolean_fallback_value(self):
        wizard = self._wizard(
            "res.partner",
            file=make_xlsx(["active"], [[datetime.date(2024, 1, 1)]], [1]),
            file_name="b.xlsx",
            file_type=XLSX_MIME,
        )
        result = wizard.execute_import(
            ["active"],
            ["active"],
            {
                "has_headers": True,
                "fallback_values": {
                    "active": {
                        "fallback_value": "true",
                        "field_model": "res.partner",
                        "field_type": "boolean",
                    }
                },
            },
        )
        self.assertIsInstance(result, dict)

    def test_selection_fallback_on_an_unknown_field_does_not_raise_keyerror(self):
        """A Properties sub-column ('<field>.<property>') is not a field of the
        model, so fields_get returned nothing for it and indexing the result
        raised KeyError.
        """
        wizard = self._wizard("res.partner")
        data = wizard._handle_fallback_values(
            ["props.mysel"],
            [["bogus"]],
            {
                "props.mysel": {
                    "fallback_value": "a",
                    "field_model": "res.partner",
                    "field_type": "selection",
                    "selection": [("a", "A"), ("b", "B")],
                }
            },
        )
        self.assertEqual(data, [["a"]], "unmatched value should take the fallback")

    def test_a_stored_selection_value_is_not_treated_as_invalid(self):
        """The accept-list was built from the LABELS:

            selection_values = [str(value).lower() for _key, value in selection]

        where `value` is the label. A cell carrying the field's own stored value
        was therefore "invalid" and was replaced by the fallback -- silently, and
        even though the converter downstream accepts it. `ir.sequence` imported
        `no_gap` as `standard` the moment a fallback was configured.
        """
        wizard = self._wizard("ir.sequence")
        data = wizard._handle_fallback_values(
            ["implementation"],
            [["no_gap"], ["Standard"], ["not_a_value"]],
            {
                "implementation": {
                    "fallback_value": "standard",
                    "field_model": "ir.sequence",
                    "field_type": "selection",
                }
            },
        )
        self.assertEqual(
            data,
            [["no_gap"], ["Standard"], ["standard"]],
            "a stored value and a label both stand; only the third is invalid",
        )

    def test_every_stored_selection_value_is_accepted_by_the_fallback_check(self):
        """The check and `ir.fields.converter` must not disagree about what is
        valid. They did: 30 stored, writable selection fields in this registry
        have at least one value the labels do not cover.
        """
        wizard = self._wizard("res.partner")
        converter = self.env["ir.fields.converter"]
        rejected = []
        for model_name in self.env.registry.models:
            model = self.env[model_name]
            if model._abstract or model._transient:
                continue
            for fname, field in model._fields.items():
                if field.type != "selection" or not field.store or field.readonly:
                    continue
                selection = None
                with contextlib.suppress(Exception):
                    selection = field._description_selection(self.env)
                if not selection:
                    continue
                values = [v for v, _l in selection if isinstance(v, str) and v]
                if not values:
                    continue
                accepted = frozenset(converter._get_selection_index(field))
                rejected += [
                    (model_name, fname, v) for v in values if v.lower() not in accepted
                ]
        self.assertFalse(
            rejected, f"stored values the fallback check would replace: {rejected[:10]}"
        )
        # and the wiring actually puts that set where the check reads it
        fallback = {
            "implementation": {
                "fallback_value": "standard",
                "field_model": "ir.sequence",
                "field_type": "selection",
            }
        }
        wizard._handle_fallback_values(["implementation"], [["no_gap"]], fallback)
        self.assertIn("no_gap", fallback["implementation"]["accepted_values"])

    def test_a_boolean_token_the_converter_accepts_is_not_replaced(self):
        """The boolean branch tested against a hard-coded

            ("0", "1", "true", "false")

        while the converter also accepts `yes`/`no` and every installed
        language's translations of all four. A cell saying `yes` was replaced by
        the fallback -- so `active,yes` with a `false` fallback archived the
        record the file asked to keep.
        """
        wizard = self._wizard("res.partner")
        fallback = {
            "active": {
                "fallback_value": "false",
                "field_model": "res.partner",
                "field_type": "boolean",
            }
        }
        data = wizard._handle_fallback_values(
            ["active"],
            [["yes"], ["no"], ["1"], ["true"], ["maybe"]],
            fallback,
        )
        self.assertEqual(
            data,
            [["yes"], ["no"], ["1"], ["true"], ["false"]],
            "only the token the converter cannot read takes the fallback",
        )
        trues, falses = self.env["ir.fields.converter"]._get_boolean_tokens()
        self.assertEqual(fallback["active"]["accepted_values"], trues | falses)

    def test_a_fallback_on_a_third_field_type_leaves_the_cell_alone(self):
        """Only boolean and selection get an accept-list. Indexing it
        unconditionally would turn a client sending any other `field_type` into
        a KeyError, which `execute_import` does not catch -- an HTTP 500.
        """
        wizard = self._wizard("res.partner")
        data = wizard._handle_fallback_values(
            ["name"],
            [["Acme"]],
            {
                "name": {
                    "fallback_value": "x",
                    "field_model": "res.partner",
                    "field_type": "char",
                }
            },
        )
        self.assertEqual(data, [["Acme"]])

    def test_skip_leaves_a_genuinely_invalid_cell_empty(self):
        wizard = self._wizard("ir.sequence")
        data = wizard._handle_fallback_values(
            ["implementation"],
            [["no_gap"], ["not_a_value"]],
            {
                "implementation": {
                    "fallback_value": "skip",
                    "field_model": "ir.sequence",
                    "field_type": "selection",
                }
            },
        )
        self.assertEqual(data, [["no_gap"], [None]])


class TestNameColumn(ImportAuditCommon):
    def test_name_is_read_from_the_merged_row(self):
        """`import_fields` is rebound by _handle_multi_mapping to the
        deduplicated list, but the name was still read out of the *pre-merge*
        row. With [city, city, name] the index of 'name' is 1, which in the
        original row is the second `city` cell -- the import reported 'FR' as
        the record name.
        """
        wizard = self._csv(
            b"city,region,partner\nParis,FR,ACME Corp\n", res_model="res.partner"
        )
        result = wizard.execute_import(
            ["city", "city", "name"], ["city", "region", "partner"], dict(CSV_OPTS)
        )
        self.assertFalse(result.get("messages"))
        self.assertEqual(result["name"], ["ACME Corp"])
        partner = self.env["res.partner"].browse(result["ids"])
        self.assertEqual(partner.city, "Paris FR")


class TestBatchWindow(ImportAuditCommon):
    def test_url_fetches_are_limited_to_the_batch(self):
        """Only `load` honoured the batch limit, so `_parse_import_data` -- which
        *downloads remote image URLs* -- ran over the whole remainder on every
        batch: 50 URLs at limit 5 meant 50 fetches in the first batch and 275
        over the import instead of 50.
        """
        calls = []
        wizard = self._csv(
            (
                "image_1920\n"
                + "".join(f"http://example.invalid/{i}.png\n" for i in range(50))
            ).encode(),
            res_model="res.partner",
        )
        options = dict(CSV_OPTS, limit=5)
        with (
            patch.object(
                Base_ImportImport,
                "_import_file_by_url",
                lambda self, url, s, f, n: calls.append(url) or b"x",
            ),
            patch.object(
                type(self.env["res.users"]),
                "_can_import_remote_urls",
                lambda self: True,
            ),
        ):
            data, fields = wizard._convert_import_data(["image_1920"], dict(options))
            data = data[: wizard._batch_window(fields, data, 5)]
            wizard._parse_import_data(data, fields, dict(options))
        self.assertEqual(len(calls), 5)

    def test_window_keeps_one2many_continuation_rows(self):
        """`_extract_records` stops at row index `limit` but lets a record
        started before that absorb the o2m continuation rows that follow. Those
        rows must stay in the window, or the record loses part of its one2many
        lines and they are re-read as a broken record on the next batch.
        """
        wizard = self._wizard("import.o2m")
        fields = ["name", "value/name"]
        data = [
            ["rec0", "line0"],
            ["", "line1"],  # continuation of rec0
            ["", "line2"],  # continuation of rec0
            ["rec1", "line3"],
        ]
        self.assertEqual(wizard._batch_window(fields, data, 1), 3)
        self.assertEqual(wizard._batch_window(fields, data, 4), 4)

    def test_window_is_exactly_the_limit_without_one2many_columns(self):
        wizard = self._wizard("res.partner")
        data = [[f"r{i}"] for i in range(10)]
        self.assertEqual(wizard._batch_window(["name"], data, 4), 4)
        self.assertEqual(wizard._batch_window(["name"], data, 0), 10)

    def test_one2many_import_across_a_batch_boundary(self):
        """End-to-end guard for the window: the o2m lines of a record whose
        continuation rows straddle the batch limit must all land on it.
        """
        csv = b"name,value/name\nparent A,l1\n,l2\n,l3\nparent B,l4\n"
        wizard = self._csv(csv, res_model="import.o2m")
        result = wizard.execute_import(
            ["name", "value/name"], ["name", "value/name"], dict(CSV_OPTS, limit=1)
        )
        self.assertFalse(result.get("messages"))
        parent = self.env["import.o2m"].browse(result["ids"])
        self.assertEqual(parent.name, "parent A")
        self.assertEqual(sorted(parent.value.mapped("name")), ["l1", "l2", "l3"])


class TestMappingSuggestions(ImportAuditCommon):
    def test_empty_column_still_gets_a_fuzzy_suggestion(self):
        """`_extract_header_types` returns ['all'] for an all-empty column, and
        `_filter_fields_by_types` had no case for it, so only fields *with
        subfields* -- i.e. only relational ones -- survived. The header
        'Functon' matched `function` when the column had data and matched
        nothing at all when it did not.
        """
        populated = self._csv(
            b"Functon,other\nboss,x\nlead,y\n", res_model="res.partner"
        )
        empty = self._csv(b"Functon,other\n,x\n,y\n", res_model="res.partner")
        self.assertEqual(
            populated.parse_preview(dict(CSV_OPTS))["matches"],
            empty.parse_preview(dict(CSV_OPTS))["matches"],
        )

    def test_stale_saved_mapping_is_ignored(self):
        """A saved mapping outlives the field it points at. It was replayed
        verbatim at distance -1 (top priority), so the column was claimed by a
        path the client cannot resolve and ended up silently unmapped --
        suppressing the suggestion it would otherwise have received.
        """
        self.env["base_import.mapping"].create(
            {
                "res_model": "import.char",
                "column_name": "value",
                "field_name": "gone_field",
            }
        )
        result = self._csv(b"value\nx\n").parse_preview(dict(CSV_OPTS))
        self.assertEqual(result["matches"], {0: ["value"]})

    def test_negative_integers_are_typed_as_integer(self):
        """str.isdigit rejects '-1', so a column of negative integers was typed
        float/monetary and integer fields never appeared as suggestions."""
        wizard = self.env["base_import.import"]
        self.assertEqual(
            wizard._extract_header_types(["-1", "2"], {}),
            ["integer", "float", "monetary"],
        )

    def test_non_ascii_digits_are_not_typed_as_integer(self):
        """str.isdigit accepts '٣' and '²', for which int() then fails."""
        wizard = self.env["base_import.import"]
        self.assertNotIn("integer", wizard._extract_header_types(["٣", "٤"], {}))
        self.assertNotIn("integer", wizard._extract_header_types(["²"], {}))


class TestMappingStorage(ImportAuditCommon):
    def test_unmapped_columns_are_not_stored(self):
        """A `field_name = False` row was written for every column the user
        explicitly left unmapped: it can never produce a suggestion, it
        accumulates on every import, and nothing vacuums it.
        """
        wizard = self._csv(b"value,ignored\nhello,x\n")
        wizard.execute_import(["value", False], ["value", "ignored"], dict(CSV_OPTS))
        rows = self.env["base_import.mapping"].search(
            [("res_model", "=", "import.char")]
        )
        self.assertEqual(
            [(r.column_name, r.field_name) for r in rows], [("value", "value")]
        )

    def test_remapping_a_column_updates_in_place(self):
        wizard = self._csv(b"value\nhello\n")
        wizard.execute_import(["value"], ["value"], dict(CSV_OPTS))
        wizard2 = self._csv(b"value\nhello\n")
        wizard2.execute_import(["id"], ["value"], dict(CSV_OPTS))
        rows = self.env["base_import.mapping"].search(
            [("res_model", "=", "import.char")]
        )
        self.assertEqual(len(rows), 1, "the unique constraint must be respected")
        self.assertEqual(rows.field_name, "id")


class TestFieldsTree(ImportAuditCommon):
    def test_depth_is_clamped(self):
        """`get_fields_tree` is RPC-callable and `depth` was caller-supplied,
        with each level multiplying the payload ~2-4x: over JSON-RPC as a plain
        internal user, depth 3 returned 0.5 MiB, depth 7 11 MiB and depth 9
        47 MiB, and nothing refused the call.
        """
        wizard = self.env["base_import.import"]
        reference = wizard.get_fields_tree("res.partner")
        self.assertEqual(wizard.get_fields_tree("res.partner", depth=99), reference)

    def test_properties_subcolumns_are_still_published(self):
        """The properties branch was gated on `field['type'] not in 'properties'`
        -- a substring test against the string "properties" rather than a type
        comparison. It is an equality now; this pins that the branch still
        selects exactly the properties fields.
        """
        tree = self.env["base_import.import"].get_fields_tree("import.properties")
        by_name = {f["name"]: f for f in tree}
        self.assertIn("properties", by_name)
        self.assertEqual(by_name["properties"]["type"], "properties")


class TestIsolation(ImportAuditCommon):
    """`base_import.import` holds raw uploaded bytes and its ACL grants
    read+write to every internal user. Being a TransientModel confers no
    isolation -- the ORM has no transient-specific access check -- and no record
    rule shipped, so any internal user could read another user's uploaded file
    or overwrite their import by guessing the sequential id.
    """

    def test_a_user_cannot_read_another_users_import(self):
        alice = new_test_user(self.env, login="audit_alice", groups="base.group_user")
        bob = new_test_user(self.env, login="audit_bob", groups="base.group_user")
        record = (
            self.env["base_import.import"]
            .with_user(alice)
            .create(
                {
                    "res_model": "res.partner",
                    "file": b"secret",
                    "file_name": "payroll.csv",
                }
            )
        )
        self.env.flush_all()
        self.assertFalse(
            self.env["base_import.import"]
            .with_user(bob)
            .search([("id", "=", record.id)])
        )

    def test_a_user_can_still_use_their_own_import(self):
        alice = new_test_user(self.env, login="audit_alice2", groups="base.group_user")
        wizard = (
            self.env["base_import.import"]
            .with_user(alice)
            .create(
                {
                    "res_model": "import.char",
                    "file": b"value\nx\n",
                    "file_name": "t.csv",
                    "file_type": "text/csv",
                }
            )
        )
        self.env.flush_all()
        result = wizard.parse_preview(dict(CSV_OPTS))
        self.assertNotIn("error", result, result.get("error"))
