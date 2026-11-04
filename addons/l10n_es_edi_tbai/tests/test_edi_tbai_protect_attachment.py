from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestEsEdiTbaiCommonGipuzkoa


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestTbaiProtectAttachment(TestEsEdiTbaiCommonGipuzkoa):

    def test_cannot_unlink_sent_document_xml(self):
        """The XML of a document sent to the government cannot be deleted."""
        invoice = self._create_posted_invoice()
        invoice_send_wizard = self._get_invoice_send_wizard(invoice)

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            invoice_send_wizard.action_send_and_print()

        attachment = invoice.l10n_es_tbai_post_document_id.xml_attachment_id
        self.assertTrue(attachment)

        with self.assertRaises(UserError):
            attachment.unlink()

        self.assertTrue(attachment.exists())
