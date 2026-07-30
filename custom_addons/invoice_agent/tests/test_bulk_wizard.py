from odoo import fields
from odoo.tests.common import TransactionCase


class TestBulkWizard(TransactionCase):
    """Test the bulk re-extraction wizard."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        # Create a vendor bill with AI extraction data
        partner = cls.env['res.partner'].create({
            'name': 'Test Vendor',
        })
        journal = cls.env['account.journal'].search([
            ('type', '=', 'purchase'),
        ], limit=1)
        if not journal:
            journal = cls.env['account.journal'].create({
                'name': 'Test Purchase Journal',
                'type': 'purchase',
                'code': 'TPJ',
            })

        cls.move = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'ai_extraction_status': 'extracted',
            'ai_confidence': 0.45,
            'ai_ocr_text': 'INVOICE #1234\nTotal: $1,000.00',
        })

        # Add an extraction line
        cls.extraction_line = cls.env['invoice.agent.extraction.line'].create({
            'move_id': cls.move.id,
            'field_name': 'Total Amount',
            'extracted_value': '$1,000.00',
            'field_confidence': 0.85,
        })

        cls.move2 = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': partner.id,
            'invoice_date': fields.Date.today(),
            'journal_id': journal.id,
            'ai_extraction_status': 'validated',
            'ai_confidence': 0.92,
        })

    def test_wizard_prefills_move_ids_from_context(self):
        """default_get should read active_ids from context."""
        wizard = self.env['invoice.agent.bulk.process'].with_context(
            active_ids=(self.move.id, self.move2.id),
            active_model='account.move',
        ).create({})
        self.assertIn(self.move, wizard.move_ids)
        self.assertIn(self.move2, wizard.move_ids)
        self.assertEqual(len(wizard.move_ids), 2)

    def test_bulk_process_resets_extraction_state(self):
        """action_process should reset extraction status to pending."""
        wizard = self.env['invoice.agent.bulk.process'].with_context(
            active_ids=self.move.ids,
            active_model='account.move',
        ).create({})
        wizard.action_process()

        self.assertEqual(self.move.ai_extraction_status, 'pending')
        self.assertEqual(self.move.ai_confidence, 0.0)
        self.assertFalse(self.move.ai_ocr_text)

    def test_bulk_process_removes_extraction_lines(self):
        """action_process should delete associated extraction lines."""
        self.assertTrue(self.move.extraction_line_ids)

        wizard = self.env['invoice.agent.bulk.process'].with_context(
            active_ids=self.move.ids,
            active_model='account.move',
        ).create({})
        wizard.action_process()

        self.assertFalse(self.move.extraction_line_ids)

    def test_bulk_process_reports_processed_count(self):
        """action_process should return a notification with counts."""
        wizard = self.env['invoice.agent.bulk.process'].with_context(
            active_ids=(self.move.id, self.move2.id),
            active_model='account.move',
        ).create({})
        result = wizard.action_process()

        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertEqual(wizard.processed_count, 2)
        self.assertEqual(wizard.skipped_count, 0)
