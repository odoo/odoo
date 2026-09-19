import io
import unittest
import zipfile
from http import HTTPStatus
from unittest.mock import patch

import xlsxwriter
from lxml import etree

from odoo import Command, http
from odoo.libs.accel import csv_export
from odoo.libs.documents import (
    ROWS,
    Document,
    extension_for,
    get_writers,
    mimetype_for,
)
from odoo.libs.json import dumps as json_dumps
from odoo.tests.common import HttpCase, JsonRpcException, TransactionCase, tagged
from odoo.tools import mute_logger

from odoo.addons.web.controllers.export import CSVExport, ExcelExport, ExportFormat
from odoo.addons.web.controllers.export_writers import XLSX_MIMETYPE

_XLSX_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def _sheet_text(xlsx_bytes: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(xlsx_bytes)) as archive:
        shared_root = etree.fromstring(archive.read("xl/sharedStrings.xml"))
        sheet_root = etree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    shared = [
        si.findtext("m:t", default="", namespaces=_XLSX_NS)
        for si in shared_root.iterfind("m:si", _XLSX_NS)
    ]
    values = []
    for cell in sheet_root.iterfind(".//m:sheetData/m:row/m:c", _XLSX_NS):
        if cell.get("t") == "s":
            values.append(shared[int(cell.findtext("m:v", namespaces=_XLSX_NS))])
        elif cell.get("t") == "inlineStr":
            values.append(cell.findtext("m:is/m:t", default="", namespaces=_XLSX_NS))
    return " | ".join(values)


class TestCsvExportCells(unittest.TestCase):
    def test_quote_all_and_embedded_quotes(self):
        self.assertEqual(
            csv_export(["h"], [['a"b']]),
            b'"h"\r\n"a""b"\r\n',
        )

    def test_none_and_false_are_blank_but_zero_is_not(self):
        self.assertEqual(
            csv_export(["a", "b", "c", "d"], [[None, False, 0, ""]]),
            b'"a","b","c","d"\r\n"","","0",""\r\n',
        )

    def test_leading_formula_characters_are_neutralised(self):
        row = ["=cmd", "-cmd", "+cmd", "@cmd", "\tcmd", "\rcmd"]
        self.assertEqual(
            csv_export(["h"] * len(row), [row]),
            b'"h","h","h","h","h","h"\r\n'
            b'"\'=cmd","\'-cmd","\'+cmd","\'@cmd","\'\tcmd","\'\rcmd"\r\n',
        )

    def test_a_formula_character_that_is_not_leading_is_left_alone(self):
        self.assertEqual(csv_export(["h"], [["a=b"]]), b'"h"\r\n"a=b"\r\n')

    def test_non_strings_are_stringified_without_the_guard(self):
        self.assertEqual(
            csv_export(["a", "b", "c"], [[-5, 1.5, True]]),
            b'"a","b","c"\r\n"-5","1.5","True"\r\n',
        )

    def test_utf8_bytes_are_decoded(self):
        self.assertEqual(
            csv_export(["h"], [["ré".encode()]]), '"h"\r\n"ré"\r\n'.encode()
        )

    def test_undecodable_bytes_raise_unicodedecodeerror(self):
        with self.assertRaises(UnicodeDecodeError) as caught:
            csv_export(["h"], [[b"\xff\xfe"]])
        self.assertEqual(caught.exception.encoding, "utf-8")

    def test_no_rows_still_emits_the_header(self):
        self.assertEqual(csv_export(["a", "b"], []), b'"a","b"\r\n')


class ExportControllerCase(HttpCase):
    def _export(self, export_format: str, **params):
        self.authenticate("admin", "admin")
        data = json_dumps(
            {
                "model": "res.partner",
                "fields": [{"name": "name", "label": "Name", "type": "char"}],
                "ids": False,
                "domain": [],
                "import_compat": False,
                **params,
            }
        )
        return self.url_open(
            f"/web/export/{export_format}",
            data={"data": data, "csrf_token": http.Request.csrf_token(self)},
        )


@tagged("post_install", "-at_install", "web_export")
class TestExportOrder(ExportControllerCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.partner"].create(
            [
                {"name": "xordtest Victor"},
                {"name": "xordtest Alpha"},
                {"name": "xordtest Zeta"},
            ]
        )
        cls.domain = [["name", "like", "xordtest"]]

    def assert_ordered(self, haystack: str, *needles: str):
        positions = [haystack.index(needle) for needle in needles]
        self.assertEqual(
            positions,
            sorted(positions),
            f"Expected {needles} to appear in that order",
        )

    def test_csv_export_respects_order(self):
        response = self._export("csv", domain=self.domain, order="name desc")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assert_ordered(
            response.text, "xordtest Zeta", "xordtest Victor", "xordtest Alpha"
        )

    def test_csv_export_without_order_still_works(self):
        response = self._export("csv", domain=self.domain)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        for name in ("xordtest Alpha", "xordtest Victor", "xordtest Zeta"):
            self.assertIn(name, response.text)

    def test_xlsx_export_respects_order(self):
        response = self._export("xlsx", domain=self.domain, order="name asc")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assert_ordered(
            _sheet_text(response.content),
            "xordtest Alpha",
            "xordtest Victor",
            "xordtest Zeta",
        )

    def test_grouped_xlsx_export_respects_order(self):
        response = self._export(
            "xlsx",
            domain=self.domain,
            groupby=["is_company"],
            order="name desc",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assert_ordered(
            _sheet_text(response.content),
            "xordtest Zeta",
            "xordtest Victor",
            "xordtest Alpha",
        )

    @mute_logger("odoo.addons.web.controllers.export")
    def test_unknown_order_field_returns_descriptive_error(self):
        response = self._export(
            "csv", domain=self.domain, order="totally_nonexistent_zzz desc"
        )
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertIn("UserError", response.text)
        self.assertIn("Unknown order fields", response.text)
        self.assertIn("totally_nonexistent_zzz", response.text)

    @mute_logger("odoo.addons.web.controllers.export")
    def test_malformed_order_clause_returns_descriptive_error(self):
        response = self._export("csv", domain=self.domain, order="name descending")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertIn("UserError", response.text)
        self.assertIn("Invalid order clause", response.text)


@tagged("post_install", "-at_install", "web_export")
class TestNamelistStaleTemplate(HttpCase):
    def test_namelist_skips_stale_two_level_paths(self):
        export = self.env["ir.exports"].create(
            {
                "name": "stale template",
                "resource": "res.partner",
                "export_fields": [
                    Command.create({"name": "name"}),
                    Command.create({"name": "vanished_field_zzz/name"}),
                    Command.create({"name": "phone/name"}),
                    Command.create({"name": "email"}),
                ],
            }
        )
        self.authenticate("admin", "admin")
        try:
            result = self.call_jsonrpc(
                "/web/export/namelist",
                {"model": "res.partner", "export_id": export.id},
            )
        except JsonRpcException as exc:
            self.fail(f"namelist raised on a stale template: {exc}")
        self.assertEqual([field["id"] for field in result], ["name", "email"])


def _tiny_rowmax(limit: int):
    original_add_worksheet = xlsxwriter.Workbook.add_worksheet

    def add_worksheet(self, *args, **kwargs):
        worksheet = original_add_worksheet(self, *args, **kwargs)
        worksheet.xls_rowmax = limit
        return worksheet

    return patch.object(xlsxwriter.Workbook, "add_worksheet", add_worksheet)


@tagged("post_install", "-at_install", "web_export")
class TestXlsxRowLimit(ExportControllerCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.partner"].create(
            [
                {"name": "xrowtest A", "is_company": True},
                {"name": "xrowtest B", "is_company": True},
                {"name": "xrowtest C"},
                {"name": "xrowtest D"},
                {"name": "xrowtest E"},
            ]
        )
        cls.domain = [["name", "like", "xrowtest"]]

    @mute_logger("odoo.addons.web.controllers.export")
    def test_flat_export_at_row_limit_fails_loudly(self):
        with _tiny_rowmax(5):
            response = self._export("xlsx", domain=self.domain)
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertIn("UserError", response.text)
        self.assertIn("too many rows", response.text)

    def test_flat_export_at_exact_capacity_succeeds(self):
        with _tiny_rowmax(6):
            response = self._export("xlsx", domain=self.domain)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        sheet = _sheet_text(response.content)
        for suffix in "ABCDE":
            self.assertIn(f"xrowtest {suffix}", sheet)

    @mute_logger("odoo.addons.web.controllers.export")
    def test_grouped_export_header_overflow_fails_loudly(self):
        with _tiny_rowmax(7):
            response = self._export("xlsx", domain=self.domain, groupby=["is_company"])
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertIn("UserError", response.text)
        self.assertIn("too many rows", response.text)

    def test_grouped_export_within_limit_succeeds(self):
        with _tiny_rowmax(8):
            response = self._export("xlsx", domain=self.domain, groupby=["is_company"])
        self.assertEqual(response.status_code, HTTPStatus.OK)
        sheet = _sheet_text(response.content)
        for suffix in "ABCDE":
            self.assertIn(f"xrowtest {suffix}", sheet)


@tagged("post_install", "-at_install", "web_export")
class TestFormatRegistration(TransactionCase):
    def test_the_extension_and_the_mimetype_come_from_one_registration(self):
        self.assertEqual(mimetype_for("xlsx"), XLSX_MIMETYPE)
        self.assertEqual(extension_for(XLSX_MIMETYPE), "xlsx")

    def test_the_controller_derives_both_from_it(self):
        self.assertEqual(ExcelExport().content_type, XLSX_MIMETYPE)
        self.assertEqual(ExcelExport().extension, ".xlsx")
        self.assertEqual(CSVExport().content_type, "text/csv;charset=utf8")
        self.assertEqual(CSVExport().extension, ".csv")

    def test_an_unregistered_format_fails_loudly(self):
        class Nowhere(ExportFormat):
            format_key = "nowhere"

        with self.assertRaises(NotImplementedError):
            Nowhere().content_type

    def test_the_writer_is_reachable_outside_this_controller(self):
        writers = get_writers(XLSX_MIMETYPE, ROWS)
        self.assertEqual([w.name for w in writers], ["xlsx"])

    def test_a_document_can_be_written_through_the_registry(self):
        document = Document.of(
            rows=[["Ref", "Amount"], ["INV/1", 10.5]],
            mimetype=XLSX_MIMETYPE,
            columns_headers=["Ref", "Amount"],
            env=self.env,
        )
        self.assertEqual(document.mimetype, XLSX_MIMETYPE)
        self.assertIn("INV/1", _sheet_text(document.data))


@tagged("post_install", "-at_install", "web_export")
class TestExportMaxRows(ExportControllerCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.partner"].create([{"name": f"xmaxrowtest {i}"} for i in range(5)])
        cls.domain = [["name", "like", "xmaxrowtest"]]

    def test_domain_export_is_capped_by_web_export_max_rows(self):
        self.env["ir.config_parameter"].sudo().set_param("web.export_max_rows", "2")
        response = self._export("csv", domain=self.domain)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        rows = [line for line in response.text.splitlines()[1:] if line]
        self.assertEqual(len(rows), 2)

    def test_ids_export_is_not_capped_by_web_export_max_rows(self):
        self.env["ir.config_parameter"].sudo().set_param("web.export_max_rows", "2")
        partner_ids = self.env["res.partner"].search(self.domain).ids
        response = self._export("csv", ids=partner_ids, domain=[])
        self.assertEqual(response.status_code, HTTPStatus.OK)
        rows = [line for line in response.text.splitlines()[1:] if line]
        self.assertEqual(len(rows), 5)
