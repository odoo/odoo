# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tools
import odoo
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestPoSWithFiscalPosition(TestPoSCommon):
    """ Tests to pos orders with fiscal position.

    keywords/phrases: fiscal position
    """

    @classmethod
    def setUpClass(cls):
        super(TestPoSWithFiscalPosition, cls).setUpClass()

        cls.config = cls.basic_config

        cls.new_tax_17 = cls.env['account.tax'].create({'name': 'New Tax 17%', 'amount': 17})
        cls.new_tax_17.invoice_repartition_line_ids.write({'account_id': cls.tax_received_account.id})

        cls.fpos = cls._create_fiscal_position()
        cls.fpos_no_tax_dest = cls._create_fiscal_position_no_tax_dest()

        cls.product1 = cls.create_product(
            'Product 1',
            cls.categ_basic,
            lst_price=10.99,
            standard_price=5.0,
            tax_ids=cls.taxes['tax7'].ids,
        )
        cls.product2 = cls.create_product(
            'Product 2',
            cls.categ_basic,
            lst_price=19.99,
            standard_price=10.0,
            tax_ids=cls.taxes['tax10'].ids,
        )
        cls.product3 = cls.create_product(
            'Product 3',
            cls.categ_basic,
            lst_price=30.99,
            standard_price=15.0,
            tax_ids=cls.taxes['tax7'].ids,
        )
        cls.adjust_inventory([cls.product1, cls.product2, cls.product3], [100, 50, 50])

    @classmethod
    def _create_fiscal_position(cls):
        fpos = cls.env['account.fiscal.position'].create({'name': 'Test Fiscal Position'})

        account_fpos = cls.env['account.fiscal.position.account'].create({
            'position_id': fpos.id,
            'account_src_id': cls.sale_account.id,
            'account_dest_id': cls.other_sale_account.id,
        })
        tax_fpos = cls.env['account.fiscal.position.tax'].create({
            'position_id': fpos.id,
            'tax_src_id': cls.taxes['tax7'].id,
            'tax_dest_id': cls.new_tax_17.id,
        })
        fpos.write({
            'account_ids': [(6, 0, account_fpos.ids)],
            'tax_ids': [(6, 0, tax_fpos.ids)],
        })
        return fpos

    @classmethod
    def _create_fiscal_position_no_tax_dest(cls):
        fpos_no_tax_dest = cls.env['account.fiscal.position'].create({'name': 'Test Fiscal Position'})
        account_fpos = cls.env['account.fiscal.position.account'].create({
            'position_id': fpos_no_tax_dest.id,
            'account_src_id': cls.sale_account.id,
            'account_dest_id': cls.other_sale_account.id,
        })
        tax_fpos = cls.env['account.fiscal.position.tax'].create({
            'position_id': fpos_no_tax_dest.id,
            'tax_src_id': cls.taxes['tax7'].id,
        })
        fpos_no_tax_dest.write({
            'account_ids': [(6, 0, account_fpos.ids)],
            'tax_ids': [(6, 0, tax_fpos.ids)],
        })
        return fpos_no_tax_dest

    def test_01_no_invoice_fpos(self):
        """ orders without invoice

        Orders
        ======
        +---------+----------+---------------+----------+-----+---------+-----------------+--------+
        | order   | payments | invoiced?     | product  | qty | untaxed | tax             |  total |
        +---------+----------+---------------+----------+-----+---------+-----------------+--------+
        | order 1 | cash     | yes, customer | product1 |  10 |  109.90 | 18.68 [7%->17%] | 128.58 |
        |         |          |               | product2 |  10 |  181.73 | 18.17 [10%]     | 199.90 |
        |         |          |               | product3 |  10 |  309.90 | 52.68 [7%->17%] | 362.58 |
        +---------+----------+---------------+----------+-----+---------+-----------------+--------+
        | order 2 | cash     | yes, customer | product1 |   5 |   54.95 | 9.34 [7%->17%]  |  64.29 |
        |         |          |               | product2 |   5 |   90.86 | 9.09 [10%]      |  99.95 |
        +---------+----------+---------------+----------+-----+---------+-----------------+--------+
        | order 3 | bank     | no            | product2 |   5 |   90.86 | 9.09 [10%]      |  99.95 |
        |         |          |               | product3 |   5 |  154.95 | 10.85 [7%]      |  165.8 |
        +---------+----------+---------------+----------+-----+---------+-----------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -154.95 |  (for the 7% base amount)
        | sale_account        |  -90.86 |  (for the 10% base amount)
        | other_sale_account  | -474.75 |  (for the 17% base amount)
        | other_sale_account  | -272.59 |  (for the 10% base amount)
        | tax 17%             |  -80.70 |
        | tax 10%             |  -36.35 |
        | tax 7%              |  -10.85 |
        | pos receivable bank |  265.75 |
        | pos receivable cash |  855.30 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """

        self.customer.write({'property_account_position_id': self.fpos.id})
        self.open_new_session()

        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product2, 10), (self.product3, 10)],
            customer=self.customer
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product2, 5)],
            customer=self.customer,
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 5), (self.product3, 5)],
            payments=[(self.bank_pm, 265.75)],
        ))
        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        lines_balance = [-154.95, -90.86]
        self.assertEqual(len(sale_account_lines), len(lines_balance))
        for balance, amount in zip(sorted(sale_account_lines.mapped('balance')), sorted(lines_balance)):
            self.assertAlmostEqual(balance, amount)

        other_sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.other_sale_account)
        lines_balance = [-474.75, -272.59]
        self.assertEqual(len(other_sale_account_lines), len(lines_balance))
        for balance, amount in zip(sorted(other_sale_account_lines.mapped('balance')), sorted(lines_balance)):
            self.assertAlmostEqual(balance, amount)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 265.75)

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 855.3)

        manually_calculated_taxes = (-80.7, -36.35, -10.85)
        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(len(manually_calculated_taxes), len(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        self.assertTrue(receivable_line_cash.full_reconcile_id)

    def test_02_no_invoice_fpos_no_tax_dest(self):
        """ Customer with fiscal position that maps a tax to no tax.

        Orders
        ======
        +---------+----------+---------------+----------+-----+---------+-------------+--------+
        | order   | payments | invoiced?     | product  | qty | untaxed | tax         |  total |
        +---------+----------+---------------+----------+-----+---------+-------------+--------+
        | order 1 | bank     | yes, customer | product1 |  10 |  109.90 | 0           | 109.90 |
        |         |          |               | product2 |  10 |  181.73 | 18.17 [10%] | 199.90 |
        |         |          |               | product3 |  10 |  309.90 | 0           | 309.90 |
        +---------+----------+---------------+----------+-----+---------+-------------+--------+
        | order 2 | cash     | yes, customer | product1 |   5 |   54.95 | 0           |  54.95 |
        |         |          |               | product2 |   5 |   90.86 | 9.09 [10%]  |  99.95 |
        +---------+----------+---------------+----------+-----+---------+-------------+--------+
        | order 3 | bank     | no            | product2 |   5 |   90.86 | 9.09 [10%]  |  99.95 |
        |         |          |               | product3 |   5 |  154.95 | 10.85 [7%]  | 165.80 |
        +---------+----------+---------------+----------+-----+---------+-------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | sale_account        | -154.95 |  (for the 7% base amount)
        | sale_account        |  -90.86 |  (for the 10% base amount)
        | other_sale_account  | -272.59 |  (for the 10% base amount)
        | other_sale_account  | -474.75 |  (no tax)
        | tax 10%             |  -36.35 |
        | tax 7%              |  -10.85 |
        | pos receivable bank |  885.45 |
        | pos receivable cash |   154.9 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """

        self.customer.write({'property_account_position_id': self.fpos_no_tax_dest.id})
        self.open_new_session()
        # create orders
        orders = []
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product2, 10), (self.product3, 10)],
            customer=self.customer,
            payments=[(self.bank_pm, 619.7)],
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product2, 5)],
            customer=self.customer,
        ))
        orders.append(self.create_ui_order_data(
            [(self.product2, 5), (self.product3, 5)],
            payments=[(self.bank_pm, 265.75)],
        ))
        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        lines_balance = [-154.95, -90.86]
        self.assertEqual(len(sale_account_lines), len(lines_balance))
        for balance, amount in zip(sorted(sale_account_lines.mapped('balance')), sorted(lines_balance)):
            self.assertAlmostEqual(balance, amount)

        other_sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.other_sale_account)
        lines_balance = [-474.75, -272.59]
        self.assertEqual(len(other_sale_account_lines), len(lines_balance))
        for balance, amount in zip(sorted(other_sale_account_lines.mapped('balance')), sorted(lines_balance)):
            self.assertAlmostEqual(balance, amount)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 885.45)

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 154.9)

        manually_calculated_taxes = [-36.35, -10.85]
        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(len(manually_calculated_taxes), len(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        self.assertTrue(receivable_line_cash.full_reconcile_id)

    def test_03_invoiced_fpos(self):
        """ Invoice 2 orders.

        Orders
        ======
        +---------+----------+---------------------+----------+-----+---------+-----------------+--------+
        | order   | payments | invoiced?           | product  | qty | untaxed | tax             |  total |
        +---------+----------+---------------------+----------+-----+---------+-----------------+--------+
        | order 1 | bank     | yes, customer       | product1 |  10 |  109.90 | 18.68 [7%->17%] | 128.58 |
        |         |          |                     | product2 |  10 |  181.73 | 18.17 [10%]     | 199.90 |
        |         |          |                     | product3 |  10 |  309.90 | 52.68 [7%->17%] | 362.58 |
        +---------+----------+---------------------+----------+-----+---------+-----------------+--------+
        | order 2 | cash     | no, customer        | product1 |   5 |   54.95 | 9.34 [7%->17%]  |  64.29 |
        |         |          |                     | product2 |   5 |   90.86 | 9.09 [10%]      |  99.95 |
        +---------+----------+---------------------+----------+-----+---------+-----------------+--------+
        | order 3 | cash     | yes, other_customer | product2 |   5 |   90.86 | 9.09 [10%]      |  99.95 |
        |         |          |                     | product3 |   5 |  154.95 | 10.85 [7%]      | 165.80 |
        +---------+----------+---------------------+----------+-----+---------+-----------------+--------+

        Expected Result
        ===============
        +---------------------+---------+
        | account             | balance |
        +---------------------+---------+
        | other_sale_account  |  -54.95 |  (for the 17% base amount)
        | other_sale_account  |  -90.86 |  (for the 10% base amount)
        | tax 10%             |   -9.09 |
        | tax 17%             |   -9.34 |
        | pos receivable cash |  429.99 |
        | pos receivable bank |  691.06 |
        | receivable          | -691.06 |
        | other receivable    | -265.75 |
        +---------------------+---------+
        | Total balance       |     0.0 |
        +---------------------+---------+
        """

        self.customer.write({'property_account_position_id': self.fpos.id})
        self.open_new_session()
        # create orders
        orders = []
        uid1 = self.create_random_uid()
        orders.append(self.create_ui_order_data(
            [(self.product1, 10), (self.product2, 10), (self.product3, 10)],
            customer=self.customer,
            payments=[(self.bank_pm, 691.06)],
            is_invoiced=True,
            uid=uid1
        ))
        orders.append(self.create_ui_order_data(
            [(self.product1, 5), (self.product2, 5)],
            customer=self.customer,
        ))
        uid2 = self.create_random_uid()
        orders.append(self.create_ui_order_data(
            [(self.product2, 5), (self.product3, 5)],
            customer=self.other_customer,
            is_invoiced=True,
            uid=uid2,
        ))
        # sync orders
        order = self.env['pos.order'].create_from_ui(orders)

        # check values before closing the session
        self.assertEqual(3, self.pos_session.order_count)
        orders_total = sum(order.amount_total for order in self.pos_session.order_ids)
        self.assertAlmostEqual(orders_total, self.pos_session.total_payments_amount, msg='Total order amount should be equal to the total payment amount.')

        invoiced_order_1 = self.pos_session.order_ids.filtered(lambda order: uid1 in order.pos_reference)
        invoiced_order_2 = self.pos_session.order_ids.filtered(lambda order: uid2 in order.pos_reference)

        self.assertTrue(invoiced_order_1, msg='Invoiced order 1 should exist.')
        self.assertTrue(invoiced_order_2, msg='Invoiced order 2 should exist.')
        self.assertTrue(invoiced_order_1.account_move, msg='Invoiced order 1 should have invoice (account_move).')
        self.assertTrue(invoiced_order_2.account_move, msg='Invoiced order 2 should have invoice (account_move).')

        # NOTE Tests of values in the invoice accounting lines is not done here.

        # close the session
        self.pos_session.action_pos_session_validate()

        # check values after the session is closed
        session_move = self.pos_session.move_id

        sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.sale_account)
        self.assertFalse(sale_account_lines, msg='There should be no self.sale_account lines.')

        other_sale_account_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.other_sale_account)
        lines_balance = [-54.95, -90.86]
        self.assertEqual(len(other_sale_account_lines), len(lines_balance))
        for balance, amount in zip(sorted(other_sale_account_lines.mapped('balance')), sorted(lines_balance)):
            self.assertAlmostEqual(balance, amount)

        receivable_line_bank = session_move.line_ids.filtered(lambda line: self.bank_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_bank.balance, 691.06)

        receivable_line_cash = session_move.line_ids.filtered(lambda line: self.cash_pm.name in line.name)
        self.assertAlmostEqual(receivable_line_cash.balance, 429.99)

        manually_calculated_taxes = [-9.09, -9.34]
        tax_lines = session_move.line_ids.filtered(lambda line: line.account_id == self.tax_received_account)
        self.assertAlmostEqual(len(manually_calculated_taxes), len(tax_lines.mapped('balance')))
        for t1, t2 in zip(sorted(manually_calculated_taxes), sorted(tax_lines.mapped('balance'))):
            self.assertAlmostEqual(t1, t2, msg='Taxes should be correctly combined.')

        receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.receivable_account)
        self.assertAlmostEqual(receivable_line.balance, -691.06, msg='That is not the correct receivable line balance.')

        other_receivable_line = session_move.line_ids.filtered(lambda line: line.account_id == self.other_receivable_account)
        self.assertAlmostEqual(other_receivable_line.balance, -265.75, msg='That is not the correct other receivable line balance.')

        self.assertTrue(receivable_line_cash.full_reconcile_id)
        self.assertTrue(receivable_line.full_reconcile_id)
        self.assertTrue(other_receivable_line.full_reconcile_id)
