import io
from http import HTTPStatus
from unittest.mock import patch
from zipfile import ZipFile

from lxml import etree

from odoo import http
from odoo.libs.json import dumps as json_dumps
from odoo.tests.common import HttpCase, tagged


@tagged("web_http", "web_pivot")
class TestPivotExport(HttpCase):
    def test_export_xlsx_with_integer_column(self):
        self.authenticate("admin", "admin")
        jdata = {
            "title": "Sales Analysis",
            "model": "sale.report",
            "measure_count": 1,
            "origin_count": 1,
            "col_group_headers": [
                [{"title": 500, "width": 1, "height": 1}],
            ],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [
                {"title": 1, "indent": 0, "values": [{"value": 42}]},
            ],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        response.raise_for_status()
        zip_file = ZipFile(io.BytesIO(response.content))

        with zip_file.open("xl/worksheets/sheet1.xml") as file:
            sheet_tree = etree.parse(file)
        xml_data = {}

        for c in sheet_tree.iterfind(
            ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"
        ):
            cell_ref = c.attrib["r"]
            value = c.findtext(
                "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v"
            )
            xml_data[cell_ref] = value

        self.assertEqual(xml_data["B1"], "500")
        self.assertEqual(xml_data["A2"], "0")
        self.assertEqual(xml_data["B2"], "42")

    def test_export_xlsx_titles_excel_refuses_as_a_sheet_name_still_export(self):
        self.authenticate("admin", "admin")
        for title in ("Sales A/B: [2024]*?", "x" * 40, "'quoted'"):
            with self.subTest(title=title):
                jdata = {
                    "title": title,
                    "model": "res.partner",
                    "measure_count": 1,
                    "origin_count": 1,
                    "col_group_headers": [[{"title": "t", "width": 1, "height": 1}]],
                    "measure_headers": [],
                    "origin_headers": [],
                    "rows": [{"title": "r", "indent": 0, "values": [{"value": 1}]}],
                }
                response = self.url_open(
                    "/web/pivot/export_xlsx",
                    data={
                        "data": json_dumps(jdata),
                        "csrf_token": http.Request.csrf_token(self),
                    },
                )
                self.assertEqual(response.status_code, HTTPStatus.OK)
                with ZipFile(io.BytesIO(response.content)).open(
                    "xl/workbook.xml"
                ) as file:
                    name = (
                        etree.parse(file)
                        .find(
                            ".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}sheet"
                        )
                        .get("name")
                    )
                self.assertLessEqual(len(name), 31)
                self.assertFalse(set(name) & set("[]:*?/\\"))

    def test_export_xlsx_non_numeric_sizes_are_handled(self):
        self.authenticate("admin", "admin")
        jdata = {
            "title": "Bad sizes",
            "model": "res.partner",
            "measure_count": "not-a-number",
            "origin_count": 1,
            "col_group_headers": [
                [{"title": "h", "width": "wide", "height": "tall"}],
            ],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [{"title": "r", "indent": "deep", "values": [{"value": 1}]}],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(
            response.status_code,
            200,
            f"non-numeric sizes must be coerced, not 500: {response.text[:200]}",
        )

    def test_export_xlsx_oversized_cell_string_is_truncated(self):
        self.authenticate("admin", "admin")
        long_title = "A" * 100_000
        jdata = {
            "title": "Long",
            "model": "res.partner",
            "measure_count": 1,
            "origin_count": 1,
            "col_group_headers": [],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [{"title": long_title, "indent": 0, "values": [{"value": 1}]}],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        response.raise_for_status()
        zip_file = ZipFile(io.BytesIO(response.content))
        with zip_file.open("xl/sharedStrings.xml") as file:
            shared = file.read().decode()
        self.assertNotIn("A" * 32_768, shared)
        self.assertIn("A" * 32_767, shared)

    def test_export_xlsx_with_empty_data(self):
        self.authenticate("admin", "admin")

        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps({}),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertIn("No data to export", response.text)

    @patch(
        "odoo.addons.web.controllers.pivot.MAX_EXPORT_CELLS",
        5,
    )
    def test_export_xlsx_oversized_is_rejected(self):
        self.authenticate("admin", "admin")
        jdata = {
            "title": "Huge",
            "model": "sale.report",
            "measure_count": 1,
            "origin_count": 1,
            "col_group_headers": [
                [{"title": "x", "width": 50, "height": 1}],
            ],
            "measure_headers": [],
            "origin_headers": [],
            "rows": [],
        }
        response = self.url_open(
            "/web/pivot/export_xlsx",
            data={
                "data": json_dumps(jdata),
                "csrf_token": http.Request.csrf_token(self),
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.UNPROCESSABLE_ENTITY)
        self.assertIn("too large to export", response.text)
