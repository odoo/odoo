import logging

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon, AccountTestInvoicingHttpCommon
from odoo.exceptions import UserError
from odoo.tests.common import tagged

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAuditTrailDE(AccountTestInvoicingHttpCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_chart_template('de_skr03')
    def setUpClass(cls):
        super().setUpClass()
        cls.document_installed = 'documents_account' in cls.env['ir.module.module']._installed()
        if cls.document_installed:
            cls.env.user.company_id.documents_account_settings = True
            folder_test = cls.env['documents.document'].create({
                'name': 'folder_test',
                'type': 'folder',
            })
            cls.env['documents.account.folder.setting'].create({
                'folder_id': folder_test.id,
                'journal_id': cls.company_data['default_journal_sale'].id,
            })

    def _send_and_print(self, invoice):
        return self.env['account.move.send'].with_context(
            force_report_rendering=True,
        )._generate_and_send_invoices(invoice)

    def test_audit_trail_de(self):
        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'product',
                'quantity': 1,
                'price_unit': 100,
            })],
        }])
        invoice.action_post()
        self.assertFalse(invoice.message_main_attachment_id)

        # Print the invoice for the first time
        first_attachment = self._send_and_print(invoice)
        self.assertTrue(first_attachment)

        # Remove the attachment, it should only archive it instead of deleting it
        first_attachment.unlink()
        self.assertTrue(first_attachment.exists())
        # But we cannot entirely remove it
        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            first_attachment.unlink()

        # Print a second time the invoice, it generates a new attachment
        invoice.invalidate_recordset()
        second_attachment = self._send_and_print(invoice)
        self.assertNotEqual(first_attachment, second_attachment)

        # Make sure we can browse all the attachments in the UI (as it changes the main attachment)
        first_attachment.register_as_main_attachment()
        self.assertEqual(invoice.message_main_attachment_id, first_attachment)
        second_attachment.register_as_main_attachment()
        self.assertEqual(invoice.message_main_attachment_id, second_attachment)

        if self.document_installed:
            # Make sure we can change the version history of the document
            document = self.env['documents.document'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', invoice.id),
                ('name', '=ilike', '%.pdf'),
            ])
            self.assertTrue(document)
            document.attachment_id = first_attachment
            document.attachment_id = second_attachment
        else:
            _logger.runbot("Documents module is not installed, skipping part of the test")

    def test_audit_trail_write(self):
        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [Command.create({
                'name': 'product',
                'quantity': 1,
                'price_unit': 100,
            })],
        }])
        invoice.action_post()
        self.assertFalse(invoice.message_main_attachment_id)

        # Print the invoice for the first time
        self._send_and_print(invoice)
        attachment = invoice.message_main_attachment_id

        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            attachment.write({
                'res_id': self.env.user.id,
                'res_model': self.env.user._name,
            })

        with self.assertRaisesRegex(UserError, "remove parts of the audit trail"):
            attachment.datas = b'new data'
