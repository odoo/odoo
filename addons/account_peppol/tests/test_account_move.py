from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

FAKE_UUID = 'yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy'


@tagged('-at_install', 'post_install')
class TestPeppolAccountMove(AccountTestInvoicingCommon):

    _test_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_str('account_peppol.edi.mode', 'test')

    def _peppol_invoice(self, post=False):
        move = self._create_invoice(post=post)
        move.peppol_message_uuid = FAKE_UUID
        return move

    def test_cancel_and_remove_sequence_draft(self):
        move = self._peppol_invoice()
        self.assertEqual(move.state, 'draft')

        move.action_peppol_cancel_and_remove_sequence()

        self.assertEqual(move.state, 'cancel')
        self.assertEqual(move.name, '/')

    def test_reset_documents_draft_peppol(self):
        move = self._peppol_invoice()

        move.action_peppol_reset_documents()

        self.assertEqual(move.state, 'cancel')
        self.assertEqual(move.name, '/')

    def test_reset_documents_posted_peppol(self):
        move = self._peppol_invoice(post=True)
        self.assertEqual(move.state, 'posted')

        move.action_peppol_reset_documents()

        self.assertEqual(move.state, 'draft')

    def test_reset_documents_deletes_non_peppol(self):
        peppol_move = self._peppol_invoice()
        non_peppol_move = self._create_invoice()
        non_peppol_id = non_peppol_move.id

        peppol_move.action_peppol_reset_documents(ids_to_delete=[non_peppol_id])

        self.assertFalse(self.env['account.move'].browse(non_peppol_id).exists())
        self.assertTrue(peppol_move.exists())
        self.assertEqual(peppol_move.state, 'cancel')

    def test_reset_documents_skips_inalterable_hash(self):
        move = self._peppol_invoice(post=True)
        move.sudo().write({'inalterable_hash': 'fake_hash_value'})

        move.action_peppol_reset_documents()

        self.assertEqual(move.state, 'posted')

    def test_reset_documents_cancelled_peppol_untouched(self):
        move = self._peppol_invoice()
        move.button_cancel()
        self.assertEqual(move.state, 'cancel')
        original_name = move.name

        move.action_peppol_reset_documents()

        self.assertEqual(move.state, 'cancel')
        self.assertEqual(move.name, original_name)
