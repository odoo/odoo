import io

from odoo.libs.documents import ROWS, Document, get_known_reader_names, get_readers
from odoo.tests import TransactionCase, tagged

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _workbook():
    from openpyxl import Workbook

    book = Workbook()
    first = book.active
    first.title = "First"
    first.append(["ref", "total"])
    first.append(["INV/1", 139.86])
    second = book.create_sheet("Second")
    second.append(["other"])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@tagged("post_install", "-at_install")
class TestRegisteredSpreadsheetReaders(TransactionCase):
    def test_the_three_are_registered(self):
        for name in ("xlsx", "xls", "ods"):
            self.assertIn(name, get_known_reader_names())

    def test_a_workbook_yields_rows_to_any_consumer_of_the_layer(self):
        document = Document(_workbook(), name="book.xlsx")

        self.assertEqual(document.mimetype, XLSX)
        self.assertEqual(document.rows, [["ref", "total"], ["INV/1", "139.86"]])

    def test_the_sheet_names_reach_the_caller(self):
        # They were discarded until the reader was handed the document's own
        # options: a consumer got the first sheet and no way to learn of others.
        document = Document(_workbook(), name="book.xlsx")

        document.rows

        self.assertEqual(document.options["sheets"], ["First", "Second"])
        self.assertEqual(document.options["sheet"], "First")

    def test_a_caller_that_knows_which_sheet_it_wants_may_say_so(self):
        document = Document(_workbook(), name="book.xlsx", sheet="Second")

        self.assertEqual(document.rows, [["other"]])

    def test_the_default_is_still_the_first_sheet(self):
        self.assertEqual(Document(_workbook(), name="b.xlsx").rows[0], ["ref", "total"])

    def test_the_reader_declines_when_its_optional_module_is_absent(self):
        # `provides` is what keeps a missing xlrd from being an exception rather
        # than an answer, and nothing else asserts it.
        (reader,) = [r for r in get_readers(XLSX, ROWS) if r.name == "xlsx"]

        self.assertTrue(reader.provides(Document(_workbook(), name="b.xlsx")))
