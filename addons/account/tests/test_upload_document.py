# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUploadDocument(AccountTestInvoicingCommon):
    """ The methods called by the upload buttons of the views """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A real attachment: overrides like `l10n_be_soda` read it to choose how to import it
        cls.attachment = cls.env['ir.attachment'].create({'name': 'bill.pdf', 'raw': b'%PDF-1.4'})

    def _create_documents(self, record):
        with patch.object(
            self.registry['account.journal'], '_create_document_from_attachment',
            return_value=self.env['account.move'],
        ):
            return record.create_document_from_attachment(self.attachment.ids)

    def test_move_type_of_the_journal(self):
        """ Uploading on the card of a journal creates the documents of its type """
        for journal_type, move_type in (('sale', 'out_invoice'), ('purchase', 'in_invoice'), ('general', 'entry')):
            journal = self.env['account.journal'].search([
                ('type', '=', journal_type),
                ('company_id', '=', self.env.company.id),
            ], limit=1)
            action = self._create_documents(journal)
            self.assertEqual(action['context']['default_move_type'], move_type)

    def test_move_type_of_the_context(self):
        """ The type of the view is kept when uploading on the journal """
        journal = self.company_data['default_journal_purchase']
        action = self._create_documents(journal.with_context(default_move_type='in_refund'))
        self.assertEqual(action['context']['default_move_type'], 'in_refund')

    def test_invoice_views_use_the_journal_of_the_context(self):
        """ The upload buttons of the invoice views create the documents in the journal of the context """
        journal = self.company_data['default_journal_purchase']
        moves = self.env['account.move'].with_context(default_journal_id=journal.id, default_move_type='in_invoice')
        action = self._create_documents(moves)
        self.assertEqual(action['context']['default_journal_id'], journal.id)
