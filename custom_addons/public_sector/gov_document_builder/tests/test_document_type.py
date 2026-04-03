from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestGovDocumentType(TransactionCase):
    def setUp(self):
        super().setUp()
        self.document_type = self.env["gov.document.type"].create(
            {
                "name": "Tipo Base Teste",
                "code": "base_type_test",
            }
        )
        self.template = self.env["gov.document.template"].create(
            {
                "name": "Template Base Teste",
                "code": "template_base_test",
                "document_type_id": self.document_type.id,
            }
        )

    def test_create_document_type_with_valid_code(self):
        doc_type = self.env["gov.document.type"].create(
            {
                "name": "Termo de Teste",
                "code": "termo_teste_backend",
            }
        )

        self.assertEqual(doc_type.name, "Termo de Teste")
        self.assertEqual(doc_type.code, "termo_teste_backend")
        self.assertTrue(doc_type.active)

    def test_code_with_space_raises_validation_error(self):
        with self.assertRaises(ValidationError):
            self.env["gov.document.type"].create(
                {
                    "name": "Tipo Inválido",
                    "code": "tipo invalido",
                }
            )

    def test_duplicate_code_raises_integrity_error(self):
        with mute_logger("odoo.sql_db"), self.cr.savepoint(), self.assertRaises(IntegrityError):
            self.env["gov.document.type"].create(
                {
                    "name": "Tipo Duplicado",
                    "code": self.document_type.code,
                }
            )
