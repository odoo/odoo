from odoo.tests import tagged
from .common import TestInPosBase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosFlow(TestInPosBase):
    """
    Test class for GSTR-related POS functionality.
    """

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
        # session2.action_pos_session_closing_control()

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
            'amount_untaxed': 0.0,
            'amount_tax': 0.0,
            'amount_total': 630.0,
        })
