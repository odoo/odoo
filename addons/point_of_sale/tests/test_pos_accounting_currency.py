# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.point_of_sale.tests.test_pos_accounting import TestPosAccounting


class TestPosMultiCurrencyPayment(TestPosAccounting):
    """ Payments made in another currency than the one of the order.

    The amount handed over by the customer is kept on the payment side only
    (statement line / account.payment): the receivable line of the order stays
    in the document currency, otherwise amount_residual would compare amounts
    expressed in two different currencies.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 1 company currency = 2.0 fx currency (latest rate of setup_other_currency)
        cls.fx_currency = cls.setup_other_currency('EUR')

    def _fx_payment(self, pm, amount=10.6):
        return [[pm, {
            'amount': amount,
            'foreign_currency_id': self.fx_currency.id,
            'amount_currency': amount * 2,
        }]]

    def test_invoiced_order_paid_in_foreign_cash(self):
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=self._fx_payment(self.cash_pm),
            products=[[self.product_6, {}]],
            extra_data={'partner_id': self.partner_1.id, 'to_invoice': True},
        )
        invoice = order.account_move
        term_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        self.assertEqual(term_lines.currency_id, invoice.currency_id, "payment_term lines must stay in the document currency")
        self.assertEqual(invoice.amount_total, 10.6)
        self.assertEqual(invoice.amount_residual, 0.0)
        self.assertIn(invoice.payment_state, ('paid', 'in_payment'))

        st_line = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)])
        self.assertEqual(st_line.amount, 10.6)
        self.assertEqual(st_line.amount_currency, 21.2)
        self.assertEqual(st_line.foreign_currency_id, self.fx_currency)
        self.close_session()

    def test_invoiced_order_paid_in_foreign_bank(self):
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=self._fx_payment(self.bank_pm),
            products=[[self.product_6, {}]],
            extra_data={'partner_id': self.partner_1.id, 'to_invoice': True},
        )
        invoice = order.account_move
        term_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        self.assertEqual(term_lines.currency_id, invoice.currency_id)
        self.assertEqual(invoice.amount_residual, 0.0)

        payment = self.env['account.payment'].search([('pos_session_id', '=', session.id)])
        self.assertEqual(payment.currency_id, self.fx_currency)
        self.assertEqual(payment.amount, 21.2)
        self.close_session()

    def test_session_closing_with_foreign_cash_payment(self):
        session = self.open_pos_session()
        self.create_pos_order(
            payment_method=self._fx_payment(self.cash_pm),
            products=[[self.product_6, {}]],
        )
        self.close_session()
        move = session.sales_move_id
        term_lines = move.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        self.assertEqual(term_lines.currency_id, move.currency_id)
        self.assertEqual(move.amount_residual, 0.0)
        self.assertTrue(all(line.reconciled for line in term_lines))

    def test_cash_out_keeps_its_sign(self):
        session = self.open_pos_session()
        session.try_cash_in_out('out', 10, 'test out', False)
        st_line = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)])
        self.assertEqual(st_line.amount, -10)
        self.close_session(amount=-10)

    def test_refund_in_foreign_cash(self):
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=self._fx_payment(self.cash_pm, amount=-10.6),
            products=[[self.product_6, {'qty': -1, 'price_subtotal': -self.product_6.lst_price}]],
            extra_data={'partner_id': self.partner_1.id, 'to_invoice': True},
        )
        st_line = self.env['account.bank.statement.line'].search([('pos_session_id', '=', session.id)])
        self.assertEqual(st_line.amount, -10.6, "a refund must take cash out of the drawer")
        self.assertEqual(st_line.amount_currency, -21.2)
        self.assertEqual(order.account_move.amount_residual, 0.0)
        self.close_session(amount=-10.6)
