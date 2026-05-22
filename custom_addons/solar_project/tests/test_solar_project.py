from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("solar_project", "post_install", "-at_install")
class TestSolarProjectBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project = cls.env["project.project"].create({"name": "Test Solar Project"})

    def test_project_created(self):
        self.assertEqual(self.project.name, "Test Solar Project")


@tagged("solar_project", "post_install", "-at_install")
class TestSolarDocumentType(TransactionCase):
    def test_document_type_created(self):
        doc_type = self.env["solar.document.type"].create(
            {
                "name": "Electricity Bill",
                "code": "bill_electricity",
            }
        )
        self.assertEqual(doc_type.code, "bill_electricity")

    def test_document_type_code_unique(self):
        self.env["solar.document.type"].create({"name": "T1", "code": "unique_code"})
        with self.assertRaises(ValidationError):
            self.env["solar.document.type"].create(
                {"name": "T2", "code": "unique_code"}
            )
