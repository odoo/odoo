from odoo import Command
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPosCashRounding(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_a.name = "AAAAAA"  # The POS only load the first 100 partners
        cls.cash_rounding_add_invoice_line = cls.env['account.cash.rounding'].create({
            'name': "cash_rounding_add_invoice_line",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })
        cls.cash_rounding_biggest_tax = cls.env['account.cash.rounding'].create({
            'name': "cash_rounding_biggest_tax",
            'rounding': 0.05,
            'rounding_method': 'HALF-UP',
            'strategy': 'biggest_tax',
            'profit_account_id': cls.env.company.default_cash_difference_income_account_id.id,
            'loss_account_id': cls.env.company.default_cash_difference_expense_account_id.id,
        })

        cls.product = cls.env['product.product'].create({
            'name': "random_product",
            'available_in_pos': True,
            'list_price': 13.67,
            'taxes_id': [Command.set(cls.company_data['default_tax_sale'].ids)],
            'pos_categ_ids': [Command.set(cls.pos_desk_misc_test.ids)],
        })

    def test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.03,
                'amount_total': 15.7,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.03,
                'amount_total': -15.7,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_not_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.03,
                'amount_total': 15.7,
                'amount_paid': 15.72,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.03,
                'amount_total': 15.72,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.03,
                'amount_total': -15.7,
                'amount_paid': -15.72,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.69,
                'amount_tax': 2.03,
                'amount_total': 15.72,
            }])

    def test_cash_rounding_halfup_biggest_tax_only_round_cash_method(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.7,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.7,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.67,
                'amount_tax': 2.03,
                'amount_total': 15.7,
            }])

    def test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash(self):
        self.skipTest('To re-introduce when feature is ready')
        self.main_pos_config.write({
            'rounding_method': self.cash_rounding_biggest_tax.id,
            'cash_rounding': True,
            'only_round_cash_method': True,
        })
        with self.with_new_session(user=self.pos_user) as session:
            self.start_pos_tour('test_cash_rounding_halfup_biggest_tax_only_round_cash_method_pay_by_bank_and_cash')
            refund, order = self.env['pos.order'].search([('session_id', '=', session.id)], limit=2)
            self.assertRecordValues(order, [{
                'amount_tax': 2.05,
                'amount_total': 15.72,
                'amount_paid': 15.73,
            }])
            self.assertRecordValues(order.account_move, [{
                'amount_untaxed': 13.70,
                'amount_tax': 2.03,
                'amount_total': 15.73,
            }])
            self.assertRecordValues(refund, [{
                'amount_tax': -2.05,
                'amount_total': -15.72,
                'amount_paid': -15.73,
            }])
            self.assertRecordValues(refund.account_move, [{
                'amount_untaxed': 13.70,
                'amount_tax': 2.03,
                'amount_total': 15.73,
            }])

    def test_archived_product_removed_and_order_is_refunded(self):
        """
        Tests that once product is archived after order is created
        product is not shown but the order can still be refunded.
        """
        self.pos_admin.write({
            'group_ids': [
                (4, self.env.ref('product.group_product_manager').id),
                (4, self.env.ref('account.group_account_manager').id),
            ]
        })
        self.env['product.product'].create({
            'is_storable': True,
            'name': 'A Test Product',
            'available_in_pos': True,
            'list_price': 1,
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        self.start_tour(
            "/pos/ui?config_id=%d" % self.main_pos_config.id,
            "test_archived_product_removed_and_order_is_refunded",
            login="pos_admin"
        )
