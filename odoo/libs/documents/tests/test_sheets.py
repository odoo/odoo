import datetime
import io
import re
import unittest
import zipfile

from odoo.libs.documents.formats import mimetype_for
from odoo.libs.documents.representations import SHEETS
from odoo.libs.documents.sheets import SheetBuilder
from odoo.libs.documents.writers import get_writers

XLSX = mimetype_for("xlsx")


def write(*sheets, **options):
    (writer,) = get_writers(XLSX, SHEETS)
    return zipfile.ZipFile(io.BytesIO(writer.write(list(sheets), **options)))


def sheet_xml(book, index=1):
    return book.read(f"xl/worksheets/sheet{index}.xml").decode()


def column_width(xml, column):
    match = re.search(
        rf'<col min="{column + 1}" max="{column + 1}" width="([\d.]+)"', xml
    )
    return float(match[1]) if match else None


class TestSheetBuilder(unittest.TestCase):
    def test_operations_are_recorded_in_call_order(self):
        sheet = SheetBuilder("S")
        sheet.cell(0, 0, "a", {"bold": True}, measure=12)
        sheet.column(0, 0, 10)
        sheet.default_row(20)
        sheet.row(0, 30)
        self.assertEqual(
            [operation[0] for operation in sheet.operations],
            ["cell", "column", "default_row", "row"],
        )

    def test_a_cell_keeps_its_own_copy_of_the_style(self):
        style = {"bold": True}
        sheet = SheetBuilder("S")
        sheet.cell(0, 0, "a", style)
        style["bold"] = False
        self.assertEqual(sheet.operations[0][4], {"bold": True})


class TestXlsxSheetsWriter(unittest.TestCase):
    def test_one_writer_turns_sheets_into_xlsx(self):
        self.assertEqual([w.name for w in get_writers(XLSX, SHEETS)], ["xlsx_sheets"])

    def test_sheet_names_are_truncated_and_made_unique(self):
        long_name = "x" * 40
        book = write(SheetBuilder(long_name), SheetBuilder(long_name))
        names = re.findall(
            r'<sheet name="([^"]+)"', book.read("xl/workbook.xml").decode()
        )
        self.assertEqual(names, ["x" * 31, "x" * 29 + "~2"])

    def test_sheet_names_follow_excels_rules_instead_of_crashing_the_export(self):
        book = write(
            SheetBuilder("Data"),
            SheetBuilder("data"),
            SheetBuilder("Q1/Q2 [draft]: *?\\"),
            SheetBuilder("'quoted'"),
            SheetBuilder("x" * 30 + "'tail"),
            SheetBuilder("/"),
        )
        names = re.findall(
            r'<sheet name="([^"]+)"', book.read("xl/workbook.xml").decode()
        )
        self.assertEqual(
            names,
            ["Data", "data~2", "Q1Q2 draft", "quoted", "x" * 30, "Sheet6"],
        )

    def test_a_measured_date_cell_does_not_crash_the_width(self):
        sheet = SheetBuilder("S")
        sheet.cell(0, 0, datetime.date(2024, 1, 31), date=True, measure=12)
        self.assertIsNotNone(column_width(sheet_xml(write(sheet)), 0))

    def test_a_measured_cell_widens_its_column_within_the_cap(self):
        sheet = SheetBuilder("S")
        sheet.cell(0, 0, "a fairly long label that needs room", measure=12)
        sheet.cell(0, 1, "w" * 500, measure=12)
        xml = sheet_xml(write(sheet))
        self.assertGreater(column_width(xml, 0), 8.43)
        self.assertAlmostEqual(column_width(xml, 1), 75.71, places=1)

    def test_an_unmeasured_or_merged_cell_leaves_the_width_alone(self):
        sheet = SheetBuilder("S")
        sheet.cell(0, 0, "a fairly long label that needs room")
        sheet.cell(1, 1, "a fairly long label that needs room", colspan=2, measure=12)
        xml = sheet_xml(write(sheet))
        self.assertIsNone(column_width(xml, 0))
        self.assertIsNone(column_width(xml, 1))
        self.assertIn('<mergeCell ref="B2:C2"/>', xml)

    def test_a_later_column_width_replaces_a_measured_one(self):
        sheet = SheetBuilder("S")
        sheet.cell(0, 0, "a fairly long label that needs room", measure=12)
        sheet.column(0, 0, 10)
        self.assertAlmostEqual(
            column_width(sheet_xml(write(sheet)), 0), 10.71, places=1
        )

    def test_row_heights_are_written(self):
        sheet = SheetBuilder("S")
        sheet.default_row(20)
        sheet.row(0, 30)
        sheet.cell(0, 0, "a")
        xml = sheet_xml(write(sheet))
        self.assertIn('defaultRowHeight="20"', xml)
        self.assertRegex(xml, r'<row r="1"[^>]* ht="30"')
