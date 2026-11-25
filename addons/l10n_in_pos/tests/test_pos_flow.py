# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestInPosBase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosFlow(TestInPosBase):
    """
    Test class for GSTR-related POS functionality.
    """
    _test_user_groups = None  # FIXME list needed groups

    def test_invoice_order_after_session_closed(self):
        """Test that an order can be invoiced after its session is closed.
        Scenario:
            1. Create a POS session and two orders:
            - Order A: Not to be invoiced immediately.
            - Order B: To be invoiced immediately.
            2. Close the POS session.
            3. Ensure:
            - Both orders have `reversed_move_ids` unset.
            4. Assign a partner to Order A and invoice it AFTER the session is closed.
            - Confirm that `reversed_move_ids` is set accordingly.
        """

        with self.with_pos_session():
            # Create a POS order without an invoice, simulating basic sale and payment
            pos_order_going_to_invoice = self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_a, 2.0),  # 2 units of product A
                    (self.product_b, 2.0),  # 2 units of product B
                ],
                'payments': [(self.bank_pm1, 630.0)],  # Payment of 630 through bank payment method
            })
            # Create a POS order with an invoice and a linked customer
            pos_order_with_invoice = self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_a, 3.0),  # 3 units of product A
                    (self.product_b, 3.0),  # 3 units of product B
                ],
                'payments': [(self.bank_pm1, 945.0)],  # Payment of 945 through bank payment method
                'customer': self.partner_a,
            })

        # Initial state: no reversal moves for both orders
        self.assertFalse(pos_order_going_to_invoice.reversed_move_ids,
                        "Order with 'to_invoice' = False should have no reversal moves after session is closed.")
        self.assertFalse(pos_order_with_invoice.reversed_move_ids,
                        "Immediate invoiced order should have no reversal moves after session is closed.")

        # Now, set a partner and invoice the order after the session is closed
        # with self.with_pos_session() as session2:
        pos_order_going_to_invoice.partner_id = self.partner_a
        pos_order_going_to_invoice.action_pos_order_invoice()

        # Confirm that reversal move(s) are now set
        reversal_moves = self.env['account.move'].search([('reversed_pos_order_id', '=', pos_order_going_to_invoice.id)])
        self.assertEqual(pos_order_going_to_invoice.reversed_move_ids, reversal_moves,
                        "Reversal move should be set for the order invoiced after the session is closed.")
        self.assertInvoiceValues(reversal_moves, [
            {'product_id': self.product_a.id, 'l10n_in_hsn_code': '1111', 'product_uom_id': self.product_a.uom_id.id, 'debit': 200.0, 'credit': 0.0},
            {'product_id': self.product_b.id, 'l10n_in_hsn_code': '2222', 'product_uom_id': self.product_b.uom_id.id, 'debit': 400.0, 'credit': 0.0},
            {'product_id': False, 'l10n_in_hsn_code': False, 'product_uom_id': False, 'debit': 15.0, 'credit': 0.0},
            {'product_id': False, 'l10n_in_hsn_code': False, 'product_uom_id': False, 'debit': 15.0, 'credit': 0.0},
            {'product_id': False, 'l10n_in_hsn_code': False, 'product_uom_id': False, 'debit': 0.0, 'credit': 630.0},
        ], {
            'move_type': 'out_refund',
            'journal_id': self.config.journal_id.id,
            'ref': f"Reversal of B2C invoice {pos_order_going_to_invoice.l10n_in_b2c_invoice_number}",
            'amount_untaxed': 600.0,
            'amount_tax': 30.0,
            'amount_total': 630.0,
        })
        self.assertEqual(pos_order_going_to_invoice.amount_total, 630.0,
                        "The total amount of the order should match the reversal move total.")

    @freeze_time('2002-11-29')
    def test_b2c_invoice_numbers(self):
        prefix = f"02/{self.config.id:02d}/"
        padding = 16 - len(f"P{prefix}")
        order_info = {
            'pos_order_lines_ui_args': [(self.product_a, 1.0)],
            'payments': [(self.bank_pm1, 105.0)],
        }
        with self.with_pos_session():
            walk_in_order = self._create_order(order_info)
            customer_order = self._create_order({
                **order_info,
                'customer': self.partner_a,
            })
            invoiced_order = self._create_order({
                **order_info,
                'customer': self.partner_a,
                'is_invoiced': True,
            })
            b2c_refund = self._create_refund_order(walk_in_order)
            b2b_refund = self._create_refund_order(invoiced_order, {'customer': self.partner_a, 'is_invoiced': True})
            invoiced_b2c_refund = self._create_refund_order(customer_order, {'customer': self.partner_a, 'is_invoiced': True})

            walk_in_order.action_pos_order_paid()

        orders = walk_in_order | customer_order | invoiced_order | b2c_refund | b2b_refund | invoiced_b2c_refund
        self.assertRecordValues(orders, [
            {'l10n_in_b2c_invoice_number': f"P{prefix}{1:0{padding}d}"},
            {'l10n_in_b2c_invoice_number': f"P{prefix}{2:0{padding}d}"},
            {'l10n_in_b2c_invoice_number': False},
            {'l10n_in_b2c_invoice_number': f"R{prefix}{1:0{padding}d}"},
            {'l10n_in_b2c_invoice_number': False},
            {'l10n_in_b2c_invoice_number': False},
        ])
        self.assertTrue(invoiced_b2c_refund.account_move)

    def test_b2c_orders_not_consolidated(self):
        order_info = {
            'pos_order_lines_ui_args': [(self.product_a, 1.0)],
            'payments': [(self.bank_pm1, 105.0)],
        }
        with self.with_pos_session():
            orders = self._create_order(order_info) | self._create_order(order_info)
        orders.partner_id = self.partner_a
        make_invoice = self.env['pos.make.invoice'].with_context(active_ids=orders.ids)

        with self.assertRaises(UserError):
            make_invoice.create({'consolidated_billing': True}).action_create_invoices()

        make_invoice.create({'consolidated_billing': False}).action_create_invoices()
        self.assertEqual(len(orders.account_move), 2)
        self.assertEqual(orders.reversed_move_ids.mapped('move_type'), ['out_refund', 'out_refund'])
