from odoo import Command
from odoo.addons.point_of_sale.tests.common import CommonPosTest, TestPoSCommon
from odoo.tests.common import tagged


@tagged('post_install', '-at_install')
class TestPosInvoiceConsolidation(TestPoSCommon, CommonPosTest):

    _test_user_groups = None  # FIXME list needed groups

    def setUp(cls):
        super().setUp()
        cls.config = cls.basic_config
        cls.user1 = cls.env.user
        cls.user2 = cls.simple_accountman
        cls.user2.group_ids = [Command.link(cls.env.ref('point_of_sale.group_pos_user').id)]
        cls.product1 = cls.create_product('Product 1', cls.categ_basic, 10.0)
        cls.product2 = cls.create_product('Product 2', cls.categ_basic, 20.0)

    def _close_session(self):
        cash_payments = self.pos_session.order_ids.payment_ids.filtered(
            lambda p: p.payment_method_id.type == 'cash'
        )
        self.pos_session.close_session_from_ui({self.cash_pm1.id: sum(cash_payments.mapped('amount'))})

    def _refund_order(self, order):
        """ Refund `order` entirely and pay the refund back in cash, as the POS UI does. """
        refund = self.env['pos.order'].browse(order.refund()['res_id'])
        self.make_payment(refund, self.cash_pm1, refund.amount_total)
        return refund

    def _consolidate(self, orders):
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=orders.ids).action_create_invoices()

    def test_ignore_generated_invoices(self):
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders_user1 = self._create_orders([{
                'pos_order_lines_ui_args': [(self.product1, 1)],
                'customer': self.customer,
                'is_invoiced': False,
                'uuid': 'u1-order',
            }])
            # This flattens the dict into the recordset
            orders_user1 = sum(orders_user1.values(), self.env['pos.order'])

        with self.with_user(self.user2.login):
            orders_user2 = self._create_orders([
                {
                    'pos_order_lines_ui_args': [(self.product1, 2)],
                    'customer': self.customer,
                    'is_invoiced': False,
                }, {
                    'pos_order_lines_ui_args': [(self.product2, 1)],
                    'customer': self.customer,
                    'is_invoiced': False,
                }
            ])
            # This flattens the dict into the recordset
            orders_user2 = sum(orders_user2.values(), self.env['pos.order'])

        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=orders_user1.ids).action_create_invoices()

        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 0, "User 2 should have no invoices")

        all_orders = orders_user1 + orders_user2
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=all_orders.ids).action_create_invoices()
        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 1, "User 2 should have one invoice")
        self.assertEqual(sum(orders_user2.mapped('amount_total')), invoice_user2.amount_total)

    def test_invoice_grouped_by_user_id(self):
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders_user1 = self._create_orders([{
                'pos_order_lines_ui_args': [(self.product1, 1)],
                'customer': self.customer,
                'is_invoiced': False,
                'uuid': 'u1-order',
            }])
            # This flattens the dict into the recordset
            orders_user1 = sum(orders_user1.values(), self.env['pos.order'])

        with self.with_user(self.user2.login):
            orders_user2 = self._create_orders([
                {
                    'pos_order_lines_ui_args': [(self.product1, 2)],
                    'customer': self.customer,
                    'is_invoiced': False,
                }, {
                    'pos_order_lines_ui_args': [(self.product2, 1)],
                    'customer': self.customer,
                    'is_invoiced': False,
                }
            ])
            # This flattens the dict into the recordset
            orders_user2 = sum(orders_user2.values(), self.env['pos.order'])

        all_orders = orders_user1 + orders_user2

        # create consolidated invoice
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=all_orders.ids).action_create_invoices()

        invoice_user1 = orders_user1.account_move
        invoice_user2 = orders_user2.account_move

        self.assertEqual(len(invoice_user1), 1, "User 1 should have one invoice")
        self.assertEqual(orders_user1.amount_total, invoice_user1.amount_total)

        self.assertEqual(len(invoice_user2), 1, "User 2 should have one invoice")
        self.assertEqual(sum(orders_user2.mapped('amount_total')), invoice_user2.amount_total)

    def test_consolidation_with_refund(self):
        """ A refund consolidated with sales that outweigh it must give a customer invoice of the net amount. """
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders = self._create_orders([
                {'pos_order_lines_ui_args': [(self.product1, 1)], 'customer': self.customer, 'is_invoiced': False, 'uuid': 'sale-1'},
                {'pos_order_lines_ui_args': [(self.product2, 1)], 'customer': self.customer, 'is_invoiced': False, 'uuid': 'sale-2'},
            ])
            refund = self._refund_order(orders['sale-1'])

        self._close_session()

        all_orders = orders['sale-1'] | orders['sale-2'] | refund
        self._consolidate(all_orders)

        invoice = all_orders.account_move
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.amount_total, 20.0)

    def test_consolidation_with_refund_outweighing_sales(self):
        """ When the refunds outweigh the sales, the consolidated document is a credit note. """
        self.open_new_session()

        with self.with_user(self.user1.login):
            orders = self._create_orders([
                {'pos_order_lines_ui_args': [(self.product2, 1)], 'customer': self.customer, 'is_invoiced': False, 'uuid': 'sale-1'},
                {'pos_order_lines_ui_args': [(self.product1, 1)], 'customer': self.customer, 'is_invoiced': False, 'uuid': 'sale-2'},
            ])
            refund = self._refund_order(orders['sale-1'])

        self._close_session()

        # sale-1 is left out of the selection, so the refund outweighs the sale: 10 - 20 = -10
        selected_orders = orders['sale-2'] | refund
        self._consolidate(selected_orders)

        invoice = selected_orders.account_move
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, 'out_refund')
        self.assertEqual(invoice.amount_total, 10.0)

    def test_consolidation_with_refund_and_cash_rounding(self):
        """ Same as test_consolidation_with_refund, but with a cash rounding method on the config. """
        self.open_new_session()

        income_acc = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        expense_acc = self.env['account.account'].search([('account_type', '=', 'expense')], limit=1)
        rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding 0.05',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': income_acc.id,
            'loss_account_id': expense_acc.id,
        })
        self.config.write({
            'cash_rounding': True,
            'only_round_cash_method': False,
            'rounding_method': rounding.id,
        })

        with self.with_user(self.user1.login):
            orders = self._create_orders([
                {'pos_order_lines_ui_args': [(self.product1, 1)], 'customer': self.customer, 'is_invoiced': False, 'uuid': 'sale-1'},
                {'pos_order_lines_ui_args': [(self.product2, 1)], 'customer': self.customer, 'is_invoiced': False, 'uuid': 'sale-2'},
            ])
            refund = self._refund_order(orders['sale-1'])

        self._close_session()

        all_orders = orders['sale-1'] | orders['sale-2'] | refund
        self._consolidate(all_orders)

        invoice = all_orders.account_move
        self.assertEqual(len(invoice), 1)
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.amount_total, 20.0)
        rounding_lines = invoice.line_ids.filtered(lambda line: line.display_type == 'rounding')
        self.assertEqual(sum(rounding_lines.mapped('balance')), 0.0, "nothing to round, so no rounding line should compensate anything")

    def test_consolidation_non_cash_with_cash_rounding_enabled(self):
        """Cash rounding enabled, consolidate +/- orders paid non-cash; force delta; no crash."""
        self.open_new_session()

        income_acc = self.env['account.account'].search([('account_type', '=', 'income')], limit=1)
        expense_acc = self.env['account.account'].search([('account_type', '=', 'expense')], limit=1)

        rounding = self.env['account.cash.rounding'].create({
            'name': 'Rounding 0.05',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': income_acc.id,
            'loss_account_id': expense_acc.id,
        })

        self.config.write({
            'cash_rounding': True,
            'only_round_cash_method': True,
            'rounding_method': rounding.id,
        })

        non_cash_pm = self.config.payment_method_ids.filtered(lambda pm: pm.type != 'cash')[:1]
        self.assertTrue(non_cash_pm, "Need at least one non-cash payment method on the POS config.")
        self.product2.lst_price = 9.99
        with self.with_user(self.user1.login):
            orders = self._create_orders([
                {'pos_order_lines_ui_args': [(self.product1, 1)], 'customer': self.customer, 'is_invoiced': False},
                {
                    'pos_order_lines_ui_args': [(self.product2, 1)],
                    'customer': self.customer,
                    'is_invoiced': False,
                    'payments': [(self.cash_pm1, 10)]},
            ])
            orders = sum(orders.values(), self.env['pos.order'])

        self.assertEqual(len(orders), 2, "Should have created 2 orders")
        self.assertEqual(orders.mapped('amount_total'), [10.0, 9.99])
        self.assertEqual(orders.mapped('amount_paid'), [10.0, 10.0])
        self.assertEqual(orders.mapped('amount_difference'), [0.0, 0.01])
        self.assertEqual(orders.mapped('amount_return'), [0.0, 0.0])
        self.env['pos.make.invoice'].create({'consolidated_billing': True}).with_context(active_ids=orders.ids).action_create_invoices()
        self.assertEqual(len(orders.account_move), 1)


import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosMargin(TestPoSCommon):
    """
    Test the margin computation on orders with basic configuration
    The tests contain the base scenarios.
    """
    _test_user_groups = None  # FIXME list needed groups

    def setUp(self):
        super(TestPosMargin, self).setUp()
        self.config = self.basic_config
        self.uom_unit = self.env.ref('uom.product_uom_unit')


    def test_positive_margin(self):
        """
        Test margin where it should be more than zero
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 20)
        self.assertEqual(self.pos_session.order_ids[2].margin, 50)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.close_session_from_ui()

    def test_negative_margin(self):
        """
        Test margin where it should be less than zero
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 15)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 100)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, -5)
        self.assertEqual(self.pos_session.order_ids[1].margin, -50)
        self.assertEqual(self.pos_session.order_ids[2].margin, -110)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, -0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, -1)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), -0.92)

        # close session
        self.pos_session.close_session_from_ui()

    def test_full_margin(self):
        """
        Test margin where the product cost is always 0
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10)
        product2 = self.create_product('Product 2', self.categ_basic, 50)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 10)
        self.assertEqual(self.pos_session.order_ids[1].margin, 50)
        self.assertEqual(self.pos_session.order_ids[2].margin, 120)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 1)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 1)
        self.assertEqual(self.pos_session.order_ids[2].margin_percent, 1)

        # close session
        self.pos_session.close_session_from_ui()

    def test_tax_margin(self):
        """
        Test margin with tax on products
        Product 1 price without tax = 10
        Product 2 price without tax = 50
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5, self.taxes['tax7'].ids)
        product2 = self.create_product('Product 2', self.categ_basic, 55, 30, self.taxes['tax10'].ids)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, 5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 20)
        self.assertEqual(self.pos_session.order_ids[2].margin, 50)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.close_session_from_ui()

    def test_other_currency_margin(self):
        """
        Test margin with tax on products and with different currency
        The currency rate is 0.5 so the product price is halved in this currency.
        """

        # change the config
        current_config = self.config
        self.config = self.other_currency_config

        # same parameters as test_positive_margin
        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins in the config currency
        self.assertEqual(self.pos_session.order_ids[0].margin, 2.5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 10)
        self.assertEqual(self.pos_session.order_ids[2].margin, 25)

        # check margins percent which should be the same as test_positive_margin
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.close_session_from_ui()

        # set the config back
        self.config = current_config

    def test_tax_and_other_currency_margin(self):
        """
        Test margin with different currency between products and config with taxes.
        Product 1 price without tax = 10
        Product 2 price without tax = 50
        The currency rate is 0.5 so the product price is halved in this currency.
        """

        # change the config
        current_config = self.config
        self.config = self.other_currency_config

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5, self.taxes['tax7'].ids)
        product2 = self.create_product('Product 2', self.categ_basic, 55, 30, self.taxes['tax10'].ids)

        # open a session
        self.open_new_session()

        # create orders
        orders = [self.create_ui_order_data([(product1, 1)]),
                  self.create_ui_order_data([(product2, 1)]),
                  self.create_ui_order_data([(product1, 2), (product2, 2)])]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins in the config currency
        self.assertEqual(self.pos_session.order_ids[0].margin, 2.5)
        self.assertEqual(self.pos_session.order_ids[1].margin, 10)
        self.assertEqual(self.pos_session.order_ids[2].margin, 25)

        # check margins percent which should be the same as test_tax_margin
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(self.pos_session.order_ids[2].margin_percent, 0.4167)

        # close session
        self.pos_session.close_session_from_ui()

        # set the config back
        self.config = current_config

    def test_return_margin(self):
        """
        Test margin where we return product (negative line quantity)
        """

        product1 = self.create_product('Product 1', self.categ_basic, 10, 5)
        product2 = self.create_product('Product 2', self.categ_basic, 50, 30)

        # open a session
        self.open_new_session()

        # create orders
        orders = [
            self.create_ui_order_data([(product1, -1)], pos_order_ui_args={'is_refund': True}),
            self.create_ui_order_data([(product2, -1)], pos_order_ui_args={'is_refund': True}),
            self.create_ui_order_data([(product1, -2), (product2, -2)], pos_order_ui_args={'is_refund': True}),
        ]

        # sync orders
        self.env['pos.order'].sync_from_ui(orders)

        # check margins
        self.assertEqual(self.pos_session.order_ids[0].margin, -5)
        self.assertEqual(self.pos_session.order_ids[1].margin, -20)
        self.assertEqual(self.pos_session.order_ids[2].margin, -50)

        # check margins percent
        self.assertEqual(self.pos_session.order_ids[0].margin_percent, 0.5)
        self.assertEqual(self.pos_session.order_ids[1].margin_percent, 0.4)
        self.assertEqual(round(self.pos_session.order_ids[2].margin_percent, 2), 0.42)

        # close session
        self.pos_session.close_session_from_ui()
