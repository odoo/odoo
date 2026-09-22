from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestExportMimeType(TransactionCase):
    """What a report export's file type means, now that one table answers it."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["report.formula"]

    def test_the_seven_types_this_replaced_still_answer(self):
        self.assertEqual(
            {
                file_type: self.report.get_export_mime_type(file_type)
                for file_type in ("xlsx", "pdf", "xml", "txt", "csv", "zip")
            },
            {
                "xlsx": (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                "pdf": "application/pdf",
                "xml": "application/xml",
                "txt": "text/plain",
                "csv": "text/csv",
                "zip": "application/zip",
            },
        )

    def test_an_unknown_file_type_is_still_false(self):
        self.assertFalse(self.report.get_export_mime_type("nonsense"))
        self.assertFalse(self.report.get_export_mime_type(""))
