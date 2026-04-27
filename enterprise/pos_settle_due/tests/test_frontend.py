import odoo
from odoo import Command
from odoo.addons.point_of_sale.tests.common import TestPoSCommon
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSSettleDueHttpCommon(TestPointOfSaleHttpCommon, TestPoSCommon):

    def test_pos_reconcile(self):
        # create customer account payment method
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        # add customer account payment method to pos config
        self.main_pos_config.write({
            'payment_method_ids': [(4, self.customer_account_payment_method.id, 0)],
        })

        self.assertEqual(self.partner_test_1.total_due, 0)

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_test_1.id,
            'lines': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
        })

        self.make_payment(order, self.customer_account_payment_method, 10.0)

        self.assertEqual(self.partner_test_1.total_due, 10)
        current_session.action_pos_session_closing_control()

        self.main_pos_config.with_user(self.user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'pos_settle_account_due', login="accountman")
        self.assertEqual(self.partner_test_1.total_due, 0)

    def test_pos_settle_due_with_rounding(self):
        self.main_pos_config.cash_rounding = True
        self.main_pos_config.only_round_cash_method = True
        self.main_pos_config.rounding_method = self.env['account.cash.rounding'].create({
            'name': '0.05 rounding method',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': self.company['default_cash_difference_income_account_id'].copy().id,
            'loss_account_id': self.company['default_cash_difference_expense_account_id'].copy().id,
            'rounding_method': 'HALF-UP',
        })

        # create customer account payment method
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        # add customer account payment method to pos config
        self.main_pos_config.write({
            'payment_method_ids': [(4, self.customer_account_payment_method.id, 0)],
        })

        self.assertEqual(self.partner_test_1.total_due, 0)

        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_test_1.id,
            'lines': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 10.02,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10.02,
                'price_subtotal_incl': 10.02,
            })],
            'amount_paid': 10.02,
            'amount_total': 10.02,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
        })

        self.make_payment(order, self.customer_account_payment_method, 10.02)

        self.assertEqual(self.partner_test_1.total_due, 10.02)
        current_session.action_pos_session_closing_control()

        self.main_pos_config.with_user(self.user).open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'test_pos_settle_due_with_rounding', login="accountman")
        self.assertEqual(self.partner_test_1.total_due, 0.00)
