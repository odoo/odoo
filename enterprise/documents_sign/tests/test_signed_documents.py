from datetime import timedelta
from freezegun import freeze_time
from psycopg2.errors import ForeignKeyViolation

from odoo.addons.documents_sign.tests.test_documents import TestCaseDocumentsBridgeSign
from odoo.tools import mute_logger


class TestSignedDocument(TestCaseDocumentsBridgeSign):
    def setUp(cls):
        super().setUp()

        sign_request = cls.create_sign_request_1_role(cls.env.user.partner_id, cls.env.user.partner_id)
        sign_request.completed_document_attachment_ids = [(4, cls.attachment.id)]

        cls.trash_doc, cls.signed_document_pdf = cls.env["documents.document"].create([
            {
                "name": "trash_doc",
                "attachment_id": cls.attachment.copy().id,
                "folder_id": cls.folder_a_a.id,
                "active": False,
            }, {
                "name": "signed document",
                "folder_id": cls.folder_a_a.id,
                "res_model": sign_request._name,
                "res_id": sign_request.id,
                "active": False,
                "attachment_id": cls.attachment.id,
            }
        ])

    def test_gc_clear_bin(self):
        """ Ensure that old, auto-deletable (in the trash) documents linked to sign requests are not
        deleted by the garbage collector.
        """

        self.assertFalse(self.signed_document_pdf.active)
        self.assertFalse(self.trash_doc.active)
        documents_deletion_date = self.signed_document_pdf.write_date + timedelta(days=self.signed_document_pdf.get_deletion_delay(), seconds=30)
        with freeze_time(documents_deletion_date):
            self.env["documents.document"]._gc_clear_bin()

        self.assertTrue(self.signed_document_pdf.exists(), "signed document should not be deleted after gc_clear_bin")
        self.assertFalse(self.trash_doc.exists(), "trash document should be deleted after gc_clear_bin")

    @mute_logger("odoo.models.unlink")
    def test_signed_document_unlink(self):
        """ Test that attempting to directly unlink a signed document raises a foreign key
        constraint error due to its link with a sign request.
        """
        self.assertFalse(self.signed_document_pdf.active)

        with (self.assertRaises(ForeignKeyViolation), self.cr.savepoint(), mute_logger("odoo.sql_db")):
            self.signed_document_pdf.unlink()
