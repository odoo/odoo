# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from .common import TestInPosBase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosFlow(TestInPosBase):
    """
    Test class for GSTR-related POS functionality.
    """
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config.default_partner_id = cls.customer

    def test_invoice_order_after_session_closed(self):
        """A B2C order invoiced to the default customer at closing is invoiced to its
        customer afterwards: its B2C invoice is cancelled by a credit note and a regular
        invoice, paid by the payments of the order, replaces it."""
        with self.with_pos_session():
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product_a, 2.0), (self.product_b, 2.0)],
                'payments': [(self.bank_pm1, 630.0)],
            })
        b2c_invoice = order.account_move
        self.assertRecordValues(b2c_invoice, [{'name': order.l10n_in_b2c_invoice_number, 'partner_id': self.customer.id}])

        order.partner_id = self.partner_a
        order.action_pos_order_invoice()

        credit_note = b2c_invoice.reversal_move_ids
        self.assertRecordValues(b2c_invoice, [{'payment_state': 'reversed'}])
        self.assertRecordValues(credit_note, [{'move_type': 'out_refund', 'state': 'posted', 'amount_total': 630.0}])
        self.assertRecordValues(order.account_move, [{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'amount_total': 630.0,
            'payment_state': 'paid',  # Paid by the payments of the order
        }])
        self.assertNotEqual(order.account_move.name, order.l10n_in_b2c_invoice_number)
        self.assertTrue(order.to_invoice)
        self.assertFalse(order.reversed_move_ids)

    def test_cron_invoices_order_with_b2c_invoice_number(self):
        """A paid order without customer gets a B2C invoice number, then the cron invoices
        it to the default customer under that number and logs the invoice on the order."""
        with self.with_pos_session():
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product_a, 1.0)],
                'payments': [(self.bank_pm1, 105.0)],
            })
            self.assertFalse(order.partner_id)
            self.assertEqual(order.l10n_in_b2c_invoice_number, order._l10n_in_format_b2c_invoice_number(1))
            self.assertTrue(order.l10n_in_b2c_invoice_number.startswith('P'))

            self.env['pos.order']._l10n_in_process_b2c_orders()

            self.assertEqual(order.account_move.name, order.l10n_in_b2c_invoice_number)
            self.assertEqual(order.partner_id, self.customer)
            self.assertEqual(order.account_move.partner_id, self.customer)
            message = order.message_ids[0]
            self.assertEqual(message.author_id, self.env.ref('base.partner_root'))
            self.assertIn(order.account_move.name, message.body)

    def test_backend_refund_uses_refund_series(self):
        """A refund made from the backend is numbered from the refund series of the PoS
        and invoiced as a credit note under that number."""
        with self.with_pos_session():
            order = self._create_order({
                'pos_order_lines_ui_args': [(self.product_a, 1.0)],
                'payments': [(self.bank_pm1, 105.0)],
            })
            refund = self.env['pos.order'].browse(order.refund()['res_id'])
            payment_context = {'active_ids': refund.ids, 'active_id': refund.id}
            self.env['pos.make.payment'].with_context(payment_context).create({
                'amount': -105.0,
                'payment_method_id': self.bank_pm1.id,
            }).with_context(payment_context).check()

            self.assertEqual(refund.l10n_in_b2c_invoice_number, refund._l10n_in_format_b2c_invoice_number(1))
            self.assertTrue(refund.l10n_in_b2c_invoice_number.startswith('R'))

            self.env['pos.order']._l10n_in_process_b2c_orders()

            self.assertEqual(refund.account_move.move_type, 'out_refund')
            self.assertEqual(refund.account_move.name, refund.l10n_in_b2c_invoice_number)
