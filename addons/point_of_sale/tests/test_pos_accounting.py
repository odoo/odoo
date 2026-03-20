# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import Form, freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestPosAccounting(AccountTestInvoicingCommon):

    @classmethod
    def _get_main_company(self):
        return self.company_data['company']

    @classmethod
    def setUpClass(self):
        super().setUpClass()
        self.main_company = self._get_main_company()
        pos_manager = self.env.ref('point_of_sale.group_pos_manager')
        self.env.user.group_ids += pos_manager

        # Create journals
        self.bank_journal = self.env['account.journal'].create({
            'name': 'Bank Test',
            'type': 'bank',
            'company_id': self.main_company.id,
            'code': 'BNK',
            'sequence': 10,
        })
        self.cash_journal = self.env['account.journal'].create({
            'name': 'Cash Test',
            'type': 'cash',
            'company_id': self.main_company.id,
            'code': 'CSH',
            'sequence': 10,
        })
        self.config_sale_journal = self.env['account.journal'].create({
            'name': 'PoS Sale',
            'type': 'sale',
            'code': 'POSS',
            'company_id': self.company.id,
            'sequence': 12,
        })

        # Accounts
        self.bank_outstanding_account = self.copy_account(
            self.inbound_payment_method_line.payment_account_id,
            {'name': 'Outstanding Bank'},
        )

        # Create payment methods
        self.cash_pm = self.env['pos.payment.method'].create({
            'name': 'Cash',
            'type': 'cash',
            'journal_id': self.cash_journal.id,
        })
        self.customer_pm = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'type': 'pay_later',
        })
        self.bank_pm = self.env['pos.payment.method'].create({
            'name': 'Bank',
            'type': 'bank',
            'journal_id': self.bank_journal.id,
            'outstanding_account_id': self.bank_outstanding_account.id,
        })

        # Create taxes with different rates
        self.tax_received_account = self.env['account.account'].create({
            'name': 'TAX_BASE',
            'code': 'TBASE',
            'account_type': 'asset_current',
        })
        tax_repartition = [
            (0, 0, {'repartition_type': 'base'}),
            (0, 0, {
                'repartition_type': 'tax',
                'account_id': self.tax_received_account.id,
            }),
        ]
        self.tax_6 = self.env['account.tax'].create({
            'name': 'Tax 6%',
            'amount_type': 'percent',
            'amount': 6,
            'invoice_repartition_line_ids': tax_repartition,
            'refund_repartition_line_ids': tax_repartition,
        })
        self.tax_12 = self.env['account.tax'].create({
            'name': 'Tax 12%',
            'amount_type': 'percent',
            'amount': 12,
            'invoice_repartition_line_ids': tax_repartition,
            'refund_repartition_line_ids': tax_repartition,
        })
        self.tax_21 = self.env['account.tax'].create({
            'name': 'Tax 21%',
            'amount_type': 'percent',
            'amount': 21,
            'invoice_repartition_line_ids': tax_repartition,
            'refund_repartition_line_ids': tax_repartition,
        })
        self.tax_fixed = self.env['account.tax'].create({
            'name': 'fixed amount tax',
            'amount_type': 'fixed',
            'amount': 1,
            'price_include_override': 'tax_excluded',
            'invoice_repartition_line_ids': tax_repartition,
            'refund_repartition_line_ids': tax_repartition,
        })

        # Create products with different tax configurations
        self.product_6 = self.env['product.product'].create({
            'name': 'Product 6%',
            'type': 'consu',
            'qty_available': 100,
            'is_storable': True,
            'list_price': 10,
            'taxes_id': [(6, 0, [self.tax_6.id])],
            'available_in_pos': True,
        })
        self.product_12 = self.env['product.product'].create({
            'name': 'Product 12%',
            'type': 'consu',
            'qty_available': 100,
            'is_storable': True,
            'list_price': 10,
            'taxes_id': [(6, 0, [self.tax_12.id])],
            'available_in_pos': True,
        })
        self.product_21 = self.env['product.product'].create({
            'name': 'Product 21%',
            'type': 'consu',
            'is_storable': True,
            'list_price': 10,
            'taxes_id': [(6, 0, [self.tax_21.id])],
            'available_in_pos': True,
        })
        self.product_6_12 = self.env['product.product'].create({
            'name': 'Product 6% + 12%',
            'type': 'consu',
            'is_storable': True,
            'list_price': 10,
            'taxes_id': [(6, 0, [self.tax_6.id, self.tax_12.id])],
            'available_in_pos': True,
        })
        taxes = [self.tax_6.id, self.tax_12.id, self.tax_21.id]
        self.product_6_12_21 = self.env['product.product'].create({
            'name': 'Product 6% + 12% + 21%',
            'type': 'consu',
            'is_storable': True,
            'list_price': 10,
            'taxes_id': [(6, 0, taxes)],
            'available_in_pos': True,
        })

        # Create different partners to use customer account
        self.partner_1 = self.env['res.partner'].create({
            'name': 'Partner 1',
        })
        self.partner_2 = self.env['res.partner'].create({
            'name': 'Partner 2',
        })

        # Create the main PoS configuration used in the tests
        revenue = self.company_data['default_account_revenue'].id
        expense = self.company_data['default_account_expense'].id
        self.rounding_method = self.env['account.cash.rounding'].create({
            'name': 'Rounding up',
            'rounding': 0.05,
            'rounding_method': 'UP',
            'profit_account_id': revenue,
            'loss_account_id': expense,
        })
        self.pos_config = self.env['pos.config'].create({
            'name': 'PoS Config',
            'journal_id': self.config_sale_journal.id,
            'payment_method_ids': [
                (4, self.cash_pm.id),
                (4, self.customer_pm.id),
                (4, self.bank_pm.id),
            ],
        })

    def get_pos_session(self):
        return self.pos_config.current_session_id

    def open_pos_session(self, opening=0, note=""):
        self.pos_config.open_ui()
        session = self.get_pos_session()
        session.set_opening_control(opening, note)
        self.assertEqual(session.state, 'opened')
        return session

    def close_session(self, amount=0):
        session = self.get_pos_session()
        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = amount or cash_details['payment_amount']
        session.close_session_from_ui({
            self.cash_pm.id: expected_cashbox_amount,
        })
        self.assertEqual(session.state, 'closed')
        return session

    def create_pos_order(self, payment_method=[], products=[], extra_data={}):
        order = {
            'amount_total': 0,
            'amount_paid': 0,
            'amount_tax': 0,
            'amount_return': 0,
            'state': 'draft',
            'date_order': fields.Datetime.to_string(fields.Datetime.now()),
            'company_id': self.env.company.id,
            'session_id': self.get_pos_session().id,
            'lines': [Command.create({
                'qty': 1,
                'product_id': product.id,
                'price_unit': product.lst_price,
                'price_subtotal': product.lst_price,
                'tax_ids': [(6, 0, product.taxes_id.ids)],
                'price_subtotal_incl': 0,
                **extra_data,
            }) for [product, extra_data] in products],
            'payment_ids': [
                Command.create({
                    'payment_method_id': pm.id,
                    **data,
                }) for [pm, data] in payment_method
            ],
            **extra_data,
        }

        data = self.env['pos.order'].sync_from_ui([order])
        order = self.env['pos.order'].browse(data['pos.order'][0]['id'])
        order._compute_prices()
        if len(payment_method):
            order_ctx = order.with_context({'generate_pdf': False})
            order_ctx._process_saved_order(False)
        return order

    def test_cash_closing_data_do_not_take_into_account_invoiced_order(self):
        session = self.open_pos_session()
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )

        # Payment amount doesn't need to be taken into account for
        # invoiced orders since the statement line is already generated
        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        self.assertEqual(cash_details['amount'], 10.6)
        self.assertEqual(cash_details['payment_amount'], 0)

    def test_invoiced_order_are_on_partner_receivable_account(self):
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.close_session()
        move = order.account_move
        self.assertNotEqual(move, session.sales_move_id)

    def test_cash_statement_opening_and_closing_consistency(self):
        def open_and_close_session_with_cash_amounts(init, start, end):
            cash_pm = self.pos_config._get_cash_payment_method()
            cash_pm.journal_id._compute_current_statement_balance()     # Force recompute in tests.
            opening_balance = self.pos_config._get_opening_balance()
            self.assertEqual(opening_balance, init)
            session = self.open_pos_session(start)
            session.close_session_from_ui({self.cash_pm.id: end})
            self.assertEqual(session.state, 'closed')
            return session.bank_statement_id

        # OPEN WITH MORE CLOSE EQUAL
        # Initial balance is 0
        # - Opening 10      line +10       balance 10
        # - Closing 10      line N/A       balance 10
        statement = open_and_close_session_with_cash_amounts(0, 10, 10)
        self.assertEqual(len(statement.line_ids), 1)
        self.assertEqual(statement.line_ids.amount, 10)
        self.assertEqual(statement.balance_end_real, 10)

        # OPEN WITH LESS CLOSE WITH MORE
        # Initial balance is 10
        # - Opening 5       line -5        balance 5
        # - Closing 10      line +5        balance 10
        statement = open_and_close_session_with_cash_amounts(10, 5, 10)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.line_ids[0].amount, -5)
        self.assertEqual(statement.line_ids[1].amount, 5)
        self.assertEqual(statement.balance_end_real, 10)

        # OPEN WITH MORE CLOSE WITH LESS
        # Initial balance is 10
        # - Opening 20      line +10       balance 20
        # - Closing 10      line -10       balance 10
        statement = open_and_close_session_with_cash_amounts(10, 20, 10)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.line_ids[0].amount, 10)
        self.assertEqual(statement.line_ids[1].amount, -10)
        self.assertEqual(statement.balance_end_real, 10)

        # OPEN EQUAL CLOSE EQUAL
        # Initial balance is 10
        # - Opening 10      line N/A       balance 10
        # - Closing 10      line N/A       balance 10
        statement = open_and_close_session_with_cash_amounts(10, 10, 10)
        self.assertEqual(len(statement.line_ids), 0)
        self.assertEqual(statement.balance_end_real, 10)

        # OPEN EQUAL CLOSE WITH MORE
        # Initial balance is 10
        # - Opening 10      line N/A       balance 10
        # - Closing 20      line +10       balance 20
        statement = open_and_close_session_with_cash_amounts(10, 10, 20)
        self.assertEqual(len(statement.line_ids), 1)
        self.assertEqual(statement.line_ids[0].amount, 10)
        self.assertEqual(statement.balance_end_real, 20)

        # OPEN EQUAL CLOSE WITH LESS
        # Initial balance is 20
        # - Opening 20      line N/A       balance 20
        # - Closing 15      line -5        balance 15
        statement = open_and_close_session_with_cash_amounts(20, 20, 15)
        self.assertEqual(len(statement.line_ids), 1)
        self.assertEqual(statement.line_ids[0].amount, -5)
        self.assertEqual(statement.balance_end_real, 15)

        # OPEN WITH LESS CLOSE EQUAL
        # Initial balance is 15
        # - Opening 10      line -5        balance 10
        # - Closing 10      line N/A       balance 10
        statement = open_and_close_session_with_cash_amounts(15, 10, 10)
        self.assertEqual(len(statement.line_ids), 1)
        self.assertEqual(statement.line_ids[0].amount, -5)
        self.assertEqual(statement.balance_end_real, 10)

        # OPEN WITH LESS CLOSE WITH LESS
        # Initial balance is 10
        # - Opening 5       line -5        balance 5
        # - Closing 3       line -2        balance 3
        statement = open_and_close_session_with_cash_amounts(10, 5, 3)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.line_ids[0].amount, -5)
        self.assertEqual(statement.line_ids[1].amount, -2)
        self.assertEqual(statement.balance_end_real, 3)

        # OPEN WITH MORE CLOSE WITH MORE
        # Initial balance is 3
        # - Opening 8       line +5        balance 8
        # - Closing 12      line +4        balance 12
        statement = open_and_close_session_with_cash_amounts(3, 8, 12)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.line_ids[0].amount, 5)
        self.assertEqual(statement.line_ids[1].amount, 4)
        self.assertEqual(statement.balance_end_real, 12)

    def test_tax_change_blocked_when_open_pos_session(self):
        """
        Changing a POS sale tax must be blocked when a POS session
        is open, this test also check if the tax is correctly marked
        as used when it's part of a PoS order line
        """
        session = self.open_pos_session()
        tax_pos = self.product_6.taxes_id
        self.assertFalse(tax_pos.is_used)

        order = self.create_pos_order(
            products=[[self.product_6, {}]],
            extra_data={'state': 'draft'},
        )
        self.assertEqual(order.lines.tax_ids, self.tax_6)               # sanity check to ensure the order line has the correct tax
        self.assertEqual(order.session_id, session)                     # sanity check to ensure the order is linked to the current session
        with self.assertRaises(UserError):
            self.tax_6.write({
                'price_include_override': 'tax_included',
            })

        tax_pos.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_pos.is_used)

    def test_classic_order(self):
        session = self.open_pos_session()
        customer_order = self.create_pos_order(
            payment_method=[[self.customer_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
            extra_data={'partner_id': self.partner_1.id},
        )

        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )

        self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )

        self.close_session()
        sale_move = session.move_ids
        cash_statement = self.cash_pm.journal_id.last_statement_id
        self.assertEqual(cash_statement, session.bank_statement_id)     # Cash statement should be the one linked to the session
        self.assertEqual(len(sale_move.line_ids), 4)                    # 3 payment_term + 1 product + 1 tax
        self.assertEqual(sale_move.amount_total, 21.2)                  # 10 + 6% tax * 2 orders (customer account order is not taken into account)
        self.assertEqual(sale_move.amount_tax, 1.2)                     # 6% tax on 30
        self.assertEqual(len(cash_statement.line_ids), 1)               # Only one line in the cash statement since the 3 orders are merged into one statement line
        self.assertEqual(cash_statement.line_ids.amount, 10.6)          # 10 + 6% tax from the cash order
        self.assertEqual(cash_statement.is_complete, True)

        # Customer account invoice
        invoice = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', self.partner_1.id),
        ])
        self.assertEqual(invoice.amount_total, 10.6)                    # 10 + 6% tax from the customer account order
        self.assertEqual(invoice.amount_tax, 0.6)                       # 6% tax on 10
        self.assertEqual(invoice.amount_residual, 10.6)                 # Not yet paid
        self.assertEqual(invoice.amount_paid, 0.0)                      # Not yet paid
        self.assertEqual(customer_order.to_invoice, True)               # Forced to True since the order is paid with a customer account

    def test_cash_statement_line(self):
        session = self.open_pos_session()

        # Cash payment of 10.6 (10 + 6% tax)
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )

        # Cash payment of 11.2 (10 + 12% tax)
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
        )

        # Cash payment of 12.0 (10 + 21% tax)
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 12.1}]],
            products=[[self.product_21, {}]],
        )

        self.close_session()
        cash_statement = self.cash_pm.journal_id.last_statement_id
        self.assertEqual(cash_statement, session.bank_statement_id)     # Cash statement should be the one linked to the session
        statement_lines = cash_statement.line_ids
        self.assertEqual(len(statement_lines), 1)
        self.assertEqual(statement_lines.amount, 33.9)                  # 10 + 6% tax + 10 + 12% tax + 10 + 21% tax

    def test_closing_entry_by_product(self):
        self.pos_config.use_closing_entry_by_product = True
        session = self.open_pos_session()

        # Create a PoS order with 2 products with different taxes
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 21.8}]],          # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[[self.product_6, {}], [self.product_12, {}]],
            extra_data={'partner_id': self.partner_1.id},
        )

        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})
        self.assertEqual(session.state, 'closed')

        sale_move = session.move_ids
        self.assertEqual(len(sale_move.line_ids), 5)                    # 1 payment_term + 2 product + 2 tax
        product_lines = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        tax_lines = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        )
        product1 = product_lines[0]
        product2 = product_lines[1]
        self.assertEqual(product1.product_id, self.product_6)           # First product line should be for product with 6% tax
        self.assertEqual(product2.product_id, self.product_12)          # Second product line should be for product with 12% tax
        self.assertEqual(product1.tax_ids.ids, [self.tax_6.id])         # First tax line should be for 6% tax
        self.assertEqual(product2.tax_ids.ids, [self.tax_12.id])        # Second tax line should be for 12% tax
        self.assertEqual(tax_lines[0].amount_currency, -0.6)            # First tax line should be at 0.6 (6% of 10)
        self.assertEqual(tax_lines[1].amount_currency, -1.2)            # Second tax line should be at 1.2 (12% of 10)

    def test_separate_invoicing_pos_order(self):
        session = self.open_pos_session()

        # Create a PoS order with 2 payment methods
        # (customer account + cash)
        pos_order = self.create_pos_order(
            payment_method=[
                [self.customer_pm, {'amount': 5.3}],
                [self.cash_pm, {'amount': 5.3}],
            ],
            products=[[self.product_6, {}]],
            extra_data={'partner_id': self.partner_1.id},
        )

        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})
        self.assertEqual(session.state, 'closed')

        # Check that the invoice is correctly created with the customer
        # account payment method
        invoice = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('partner_id', '=', self.partner_1.id),
        ])
        self.assertEqual(pos_order.account_move, invoice)               # Invoice should be linked to the PoS order
        self.assertEqual(invoice.amount_total, 10.6)                    # 10 + 6% tax from the customer account order
        self.assertEqual(invoice.amount_tax, 0.6)                       # 6% tax on 10
        self.assertEqual(invoice.amount_residual, 5.3)                  # Customer account part isn't yet paid, but cash part is paid

        # Check each account.move.line of the invoice to ensure that the
        # cash payment line is reconciled with the correct invoice line
        # (in case of multiple tax lines for example)
        payment_terms = invoice.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        cash_payment = payment_terms[0]
        customer_payment = payment_terms[1]
        self.assertEqual(cash_payment.amount_currency, 5.3)             # Cash part of the payment
        self.assertEqual(customer_payment.amount_currency, 5.3)         # Customer account part of the payment
        self.assertEqual(cash_payment.reconciled, True)                 # Cash part
        self.assertEqual(customer_payment.reconciled, False)            # Customer account part

        product_line = invoice.line_ids.filtered(
            lambda line: line.product_id == self.product_6,
        )
        product_taxes = self.product_6.taxes_id.ids
        self.assertEqual(product_line.tax_ids.ids, product_taxes)       # Taxes should be correctly copied on the invoice line
        self.assertEqual(product_line.amount_currency, -10.0)           # Product line should be at 10 (without taxes)
        self.assertEqual(product_line.credit, 10.0)                     # Product line should be a credit of 10 (without taxes)

        tax_lines = invoice.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        )
        self.assertEqual(tax_lines.amount_currency, -0.6)

    def test_fixed_tax_negative_qty_should_be_negative(self):
        service = self.env.ref('product.product_category_services').id
        zero_amount_product = self.env['product.product'].create({
            'name': 'Zero Amount Product',
            'available_in_pos': True,
            'list_price': 0,
            'taxes_id': [(6, 0, [self.tax_fixed.id])],
            'categ_id': service,
        })
        self.pos_config.write({'iface_tax_included': 'total'})

        # Test with a positive order first
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 1}]],
            products=[[zero_amount_product, {'qty': 1}]],
        )
        session.close_session_from_ui({self.cash_pm.id: 1})
        self.assertEqual(session.state, 'closed')
        move = session.move_ids
        tax_line = move.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        )
        product_line = move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        payment_line = move.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        self.assertEqual(order.amount_total, 1)                         # Total amount should be 1 since it's a fixed tax
        self.assertEqual(tax_line.credit, 1)                            # We credit the tax account with 1 since it's a fixed tax on a positive order
        self.assertEqual(tax_line.debit, 0)                             # Nothing should be debited
        self.assertEqual(product_line.debit, 0)                         # Product line should be at 0 since it's a zero amount product
        self.assertEqual(product_line.credit, 0)                        # Product line should be at 0 since it's a zero amount product
        self.assertEqual(payment_line.credit, 0)                        # Nothing should be credited since it's a payment
        self.assertEqual(payment_line.debit, 1)                         # Total amount (only taxes) should be debited to the payment line since it's a positive order

        # Now test with a negative order
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -1}]],
            products=[[zero_amount_product, {'qty': -1}]],
            extra_data={'is_refund': True},
        )
        session.close_session_from_ui({self.cash_pm.id: 0})
        self.assertEqual(session.state, 'closed')
        move = session.move_ids
        tax_line = move.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        )
        product_line = move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        payment_line = move.line_ids.filtered(
            lambda line: line.display_type == 'payment_term',
        )
        self.assertEqual(order.amount_total, -1)                        # Total amount should be 1 since it's a fixed tax
        self.assertEqual(tax_line.credit, 0)                            # Nothing should be credited since it's a refund order
        self.assertEqual(tax_line.debit, 1)                             # We debit the tax account with 1 since it's a fixed tax on a refund
        self.assertEqual(product_line.debit, 0)                         # Product line should be at 0 since it's a zero amount product
        self.assertEqual(product_line.credit, 0)                        # Product line should be at 0 since it's a zero amount product
        self.assertEqual(payment_line.credit, 1)                        # Nothing should be credited since it's a payment, but we debit the payment line with 1 since it's a refund
        self.assertEqual(payment_line.debit, 0)                         # Total amount (only taxes) should be debited to the payment line since it's a positive order

    def test_user_right_on_statement_line_for_pos_user(self):
        """Test cash difference *loss* at closing.
        """
        session = self.open_pos_session()
        session.close_session_from_ui({self.cash_pm.id: 0})
        session = self.open_pos_session()
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )
        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})
        self.assertEqual(session.state, 'closed')
        bank_statement = session.bank_statement_id
        self.assertEqual(bank_statement.balance_end_real, 10.6)         # The order is 10 + 0.60 taxes

    def test_rounding_when_closing_session(self):
        rounding_method = self.rounding_method
        rounding_method.rounding_method = 'HALF-UP'
        self.product_a.write({
            'name': 'Product Test',
            'list_price': 0.04,
            'taxes_id': False,
        })
        self.pos_config.write({
            'rounding_method': rounding_method.id,
            'cash_rounding': True,
            'only_round_cash_method': False,
        })

        def check_difference(session, difference):
            currency = self.pos_config.currency_id
            rounded = currency.round(difference)
            closing_data = session.get_closing_control_data()
            cash_details = closing_data['default_cash_details']
            expected_cashbox_amount = cash_details['payment_amount']
            session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})
            self.assertEqual(session.state, 'closed')
            rounding_lines = session.sales_move_id.line_ids.filtered(
                lambda line: line.display_type == 'rounding',
            )
            if difference > 0:
                self.assertEqual(rounding_lines.credit, rounded)
                self.assertEqual(rounding_lines.debit, 0)
            else:
                self.assertEqual(rounding_lines.debit, abs(rounded))
                self.assertEqual(rounding_lines.credit, 0)

        def create_order_and_check(amount, qty=1, pm=self.cash_pm):
            order = self.create_pos_order(
                payment_method=[[pm, {'amount': amount}]],
                products=[[self.product_a, {'qty': qty}]],
            )
            rounded = rounding_method.round(order.amount_total)
            self.assertEqual(order.amount_paid, rounded)
            self.assertEqual(order.amount_return, 0)
            return order.amount_difference

        # Only cash check when rounding amount is negative, it should be
        # debited from the move to be credited on the rounding account
        self.product_a.list_price = 0.04
        session = self.open_pos_session()
        difference = 0
        difference += create_order_and_check(0.05)                      # Rounding +0.01 (total is 0.04)
        difference += create_order_and_check(0.10, 2)                   # Rounding +0.02 (total is 0.08)
        difference += create_order_and_check(0.10, 3)                   # Rounding -0.02 (total is 0.12)
        check_difference(session, difference)                           # Difference +0.01

        # Only cash check when rounding amount is positive, it should be
        # credited from the move to be debited on the rounding account
        self.product_a.list_price = 0.06
        session = self.open_pos_session()
        difference = 0
        difference += create_order_and_check(0.05)                      # Rounding -0.01 (total is 0.04)
        difference += create_order_and_check(0.10, 2)                   # Rounding -0.02 (total is 0.12)
        check_difference(session, difference)                           # Difference -0.03

        # Round bank payment method as well
        self.product_a.list_price = 0.03
        session = self.open_pos_session()
        difference = 0
        difference += create_order_and_check(0.05, 2, self.bank_pm)     # Rounding -0.01 (total is 0.06)
        difference += create_order_and_check(0.10, 3, self.bank_pm)     # Rounding +0.01 (total is 0.09)
        check_difference(session, difference)                           # Difference 0.00

        # Try to round with mixed payment methods, both should be taken
        # into account for the rounding
        self.product_a.list_price = 0.03
        session = self.open_pos_session()
        difference = 0
        difference += create_order_and_check(0.05, 2, self.bank_pm)     # Rounding -0.01 (total is 0.06)
        difference += create_order_and_check(0.10, 4)                   # Rounding -0.02 (total is 0.12)
        check_difference(session, difference)                           # Difference -0.03

    def test_journal_entries_category_without_account(self):
        # Set company's default accounts to false
        self.env.company.income_account_id = False
        self.env.company.expense_account_id = False
        self.product_12.write({
            'property_account_income_id': False,
            'property_account_expense_id': False,
        })
        account = self.env['account.account'].create({
            'name': 'Account for category without account',
            'code': 'X1111',
        })
        self.open_pos_session()
        self.pos_config.journal_id.default_account_id = account.id
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
        )

    def test_invoice_a_negative_order_should_create_credit_note(self):
        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
            extra_data={
                'is_refund': True,
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertEqual(order.account_move.move_type, 'out_refund')    # Negative order should be flagged as a refund order

    def test_order_with_positive_and_negative_lines(self):
        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.0}]],          # 10.6 * 2 + -11.2 = = 10.0
            products=[
                [self.product_6, {'qty': 2}],
                [self.product_12, {'qty': -1}],
            ],
            extra_data={
                'partner_id': self.partner_1.id,
            },
        )
        self.close_session()
        invoice = order._generate_pos_order_invoice()
        self.assertEqual(order.amount_total, 10.0)
        self.assertEqual(invoice.amount_total, 10.0)                    # Total should be 10 since we have 2 lines at 10.6 and one line at -11.2
        self.assertEqual(invoice.move_type, 'out_invoice')              # Invoice should be flagged as a regular invoice
        self.open_pos_session()
        refund = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -10.0}]],
            products=[
                [self.product_6, {'qty': -2}],
                [self.product_12, {'qty': 1}],
            ],
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
            },
        )
        self.close_session()
        refund_invoice = refund._generate_pos_order_invoice()
        self.assertEqual(refund.amount_total, -10.0)
        self.assertEqual(refund_invoice.amount_total, 10.0)
        self.assertEqual(refund_invoice.move_type, 'out_refund')        # Refund invoice should be flagged as a refund

    def test_invoice_an_order_from_closed_session(self):
        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
            extra_data={'partner_id': self.partner_1.id},
        )
        refund = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
                'refunded_order_id': order.id,
            },
        )
        session = self.close_session()

        # Refund the sale order to check if move are correctly created
        order.action_pos_order_invoice()
        refund.action_pos_order_invoice()

        session_sales = session.sales_move_id
        session_refunds = session.refunds_move_id
        reversal_sale_move = session_sales.reversal_move_ids
        reversal_refund_move = session_refunds.reversal_move_ids

        # Check that the reversal moves have the exact opposite lines
        # than the original moves
        used_line = self.env['account.move.line']
        for sline in session_sales.line_ids:
            rline = reversal_sale_move.line_ids.filtered(
                lambda line: line.account_id == sline.account_id and not line in used_line,
            )
            used_line |= rline[0]
            self.assertEqual(sline.debit, rline[0].credit)
            self.assertEqual(sline.credit, rline[0].debit)

        used_line = self.env['account.move.line']
        for rline in session_refunds.line_ids:
            rliner = reversal_refund_move.line_ids.filtered(
                lambda line: line.account_id == rline.account_id and not line in used_line,
            )
            used_line |= rliner[0]
            self.assertEqual(rline.debit, rliner[0].credit)
            self.assertEqual(rline.credit, rliner[0].debit)

    def test_order_partial_refund_rounding(self):
        """
        This test ensures that the refund amount of a partial order
        corresponds to the price of the item, without rounding.
        """
        self.rounding_method.rounding = 5.0
        self.rounding_method.rounding_method = 'DOWN'
        self.pos_config.write({
            'rounding_method': self.rounding_method.id,
            'cash_rounding': True,
        })

        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 30}]],
            products=[[self.product_6, {'qty': 3}]],
            extra_data={'partner_id': self.partner_1.id},
        )
        rounded_amount = order._get_rounded_amount(order.amount_total)
        self.assertEqual(rounded_amount, order.amount_paid)

        refund_action = order.refund()
        refund = self.env['pos.order'].browse(refund_action['res_id'])
        with Form(refund) as refund_form:
            with refund_form.lines.edit(0) as line:
                line.qty = -1
        refund = refund_form.save()

        self.assertEqual(refund.amount_total, -10.6)
        payment_context = self.env['pos.make.payment'].with_context({
            "active_ids": refund.ids,
            "active_id": refund.id,
        })
        refund_payment = payment_context.create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_pm.id,
        })
        refund_payment.check()
        self.assertEqual(refund.amount_paid, -10)

        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})

        self.assertEqual(refund.state, 'done')
        self.assertEqual(session.state, 'closed')

    def test_pos_order_sale_and_refund_with_taxes_not_invoiced(self):
        """
        It will also check if cash_pm receivable account is correctly
        updated. Statement line should also be created with the correct
        amount.
        """
        config_partner = self.pos_config.default_partner_id
        cash_receivable = config_partner.property_account_receivable_id
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 21.8}]],          # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[[self.product_6, {}], [self.product_12, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
            },
        )
        self.assertEqual(self.product_6.qty_available, 99)              # Check that the stock of the product is correctly updated when the order is done
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -21.8}]],         # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[
                [self.product_6, {'qty': -1}],
                [self.product_12, {'qty': -1}],
            ],
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
                'refunded_order_id': order.id,
            },
        )
        self.assertEqual(self.product_6.qty_available, 100)             # Check that the stock of the product is correctly updated when the order is done

        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount']
        session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})
        self.assertEqual(session.state, 'closed')
        sale_move = session.sales_move_id
        refund_move = session.refunds_move_id

        self.assertEqual(sale_move.move_type, 'out_invoice')
        self.assertEqual(sale_move.amount_total, 21.8)
        self.assertEqual(refund_move.move_type, 'out_refund')
        self.assertEqual(refund_move.amount_total, 21.8)

        sale_product_lines = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        refund_product_lines = refund_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        self.assertEqual(len(sale_product_lines), 2)
        self.assertEqual(len(refund_product_lines), 2)
        taxes = [self.tax_6, self.tax_12]
        zippeeeed = zip(sale_product_lines, refund_product_lines, taxes)
        for sale_line, refund_line, tax in zippeeeed:
            self.assertEqual(sale_line.tax_ids, refund_line.tax_ids)
            self.assertEqual(sale_line.tax_ids.ids, tax.ids)
            self.assertEqual(sale_line.credit, refund_line.debit)

        cash_move = self.env['account.move.line'].search([
            ('account_id', '=', cash_receivable.id),
        ]).mapped('amount_currency')
        self.assertEqual([-21.8, 21.8, 21.8, -21.8], cash_move)         # The config default journal is used because cash_pm doesn't have a journal

        product_line_balance = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        ).mapped('balance')
        self.assertEqual([-10.0, -10.0], product_line_balance)          # Product lines should be at 10 (without taxes)

        tax_line_balance = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        ).mapped('balance')
        self.assertEqual([-0.6, -1.2], tax_line_balance)                # Tax lines should be at 0.6 and 1.2 for the 6

        sale_move = session.move_ids
        cash_statement = self.cash_pm.journal_id.last_statement_id
        self.assertEqual(cash_statement, session.bank_statement_id)     # Cash statement should be the one linked to the session
        cash_lines = cash_statement.line_ids.mapped('amount')
        self.assertEqual([21.8, -21.8], cash_lines)                     # One by closing entry (refund and sale)

    def test_pos_order_sale_and_refund_with_taxes_invoiced(self):
        """
        This test will check if the taxes on refunds and sales are
        correctly applied when closing the session or when invoicing
        the order.

        It will also check if cash_pm receivable account is correctly
        updated. Statement line should also be created with the correct
        amount.
        """
        cash_receivable = self.partner_1.property_account_receivable_id
        self.open_pos_session()

        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 21.8}]],          # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[[self.product_6, {}], [self.product_12, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertEqual(self.product_6.qty_available, 99)              # Check that the stock of the product is correctly updated when the order is done
        refund = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -21.8}]],         # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[
                [self.product_6, {'qty': -1}],
                [self.product_12, {'qty': -1}],
            ],
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
                'refunded_order_id': order.id,
                'to_invoice': True,
            },
        )
        self.assertEqual(self.product_6.qty_available, 100)             # Check that the stock of the product is correctly updated when the order is done
        sale_move = order.account_move
        refund_move = refund.account_move

        self.assertEqual(sale_move.move_type, 'out_invoice')
        self.assertEqual(sale_move.amount_total, 21.8)
        self.assertEqual(refund_move.move_type, 'out_refund')
        self.assertEqual(refund_move.amount_total, 21.8)

        sale_product_lines = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        refund_product_lines = refund_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        self.assertEqual(len(sale_product_lines), 2)
        self.assertEqual(len(refund_product_lines), 2)
        taxes = [self.tax_6, self.tax_12]
        zippeeeed = zip(sale_product_lines, refund_product_lines, taxes)
        for sale_line, refund_line, tax in zippeeeed:
            self.assertEqual(sale_line.tax_ids, refund_line.tax_ids)
            self.assertEqual(sale_line.tax_ids.ids, tax.ids)
            self.assertEqual(sale_line.credit, refund_line.debit)

        cash_move = self.env['account.move.line'].search([
            ('account_id', '=', cash_receivable.id),
        ]).mapped('amount_currency')
        self.assertEqual([-21.8, 21.8, 21.8, -21.8], cash_move)         # The config default journal is used because cash_pm doesn't have a journal

        product_line_balance = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        ).mapped('balance')
        self.assertEqual([-10.0, -10.0], product_line_balance)          # Product lines should be at 10 (without taxes)

        tax_line_balance = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        ).mapped('balance')
        self.assertEqual([-0.6, -1.2], tax_line_balance)                # Tax lines should be at 0.6 and 1.2 for the 6

        cash_statement = order.session_id.bank_statement_id
        cash_lines = cash_statement.line_ids.mapped('amount')
        self.assertEqual([21.8, -21.8], cash_lines)                     # One by invoice

    def test_invoiced_order_with_discount_sale_and_refund_with_tax(self):
        """
        This test will check if the taxes on refunds and sales with
        discount are correctly applied when closing the session or when
        invoicing the order.

        It will also check if cash_pm receivable account is correctly
        updated. Statement line should also be created with the correct
        amount.
        """
        cash_receivable = self.partner_1.property_account_receivable_id
        self.open_pos_session()

        order = self.create_pos_order(
            products=[
                [self.product_6, {'discount': 50}],
                [self.product_12, {'discount': 50}],
            ],
            payment_method=[[self.cash_pm, {'amount': 10.9}]],          # Total amount of the order is 5 + 6% tax + 5 + 12% tax = 10.9
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        refund = self.create_pos_order(
            products=[
                [self.product_6, {'discount': 50, 'qty': -1}],
                [self.product_12, {'discount': 50, 'qty': -1}],
            ],
            payment_method=[[self.cash_pm, {'amount': -10.9}]],         # Total amount of the order is 5 + 6% tax + 5 + 12% tax = 10.9
            extra_data={
                'partner_id': self.partner_1.id,
                'is_refund': True,
                'refunded_order_id': order.id,
                'to_invoice': True,
            },
        )
        sale_move = order.account_move
        refund_move = refund.account_move

        refund_product_line = refund_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        sale_product_line = sale_move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        zippeeeed = zip(sale_product_line, refund_product_line)
        for sale_line, refund_line in zippeeeed:
            self.assertEqual(sale_line.discount, 50)                    # Discount should be at 50%
            self.assertEqual(sale_line.discount, refund_line.discount)  # Discount should be the same on sale and refund

        self.assertEqual(sale_move.move_type, 'out_invoice')
        self.assertEqual(sale_move.amount_total, 10.9)
        self.assertEqual(refund_move.move_type, 'out_refund')
        self.assertEqual(refund_move.amount_total, 10.9)

        cash_move = self.env['account.move.line'].search([
            ('account_id', '=', cash_receivable.id),
        ]).mapped('amount_currency')
        self.assertEqual([-10.9, 10.9, 10.9, -10.9], cash_move)

    def test_pos_payment_direction_and_account(self):
        """
        Ensure POS payments create correct inbound/outbound payments
        and accounts. This test will check for invoiced orders and
        classic global entry of the session.
        """
        inbound = self.inbound_payment_method_line.payment_account_id
        self.bank_pm.outstanding_account_id = inbound.id
        config_partner = self.pos_config.default_partner_id
        pos_receivable = config_partner.property_account_receivable_id
        session = self.env['pos.session']

        def create_session_with_single_order(**kwargs):
            config = self.pos_config
            config.open_ui()
            session = self.get_pos_session()
            cash_acc = config._get_opening_balance()
            session.set_opening_control(cash_acc, "")
            order = self.create_pos_order(**kwargs)
            self.assertEqual(order.state, 'paid')
            closing_data = session.get_closing_control_data()
            cash_details = closing_data['default_cash_details']
            expected_cashbox_amount = cash_details['amount']
            session.close_session_from_ui({self.cash_pm.id: expected_cashbox_amount})
            self.assertEqual(session.state, 'closed')
            return session

        session |= create_session_with_single_order(
            payment_method=[[self.bank_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )
        session |= create_session_with_single_order(
            payment_method=[[self.bank_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
            extra_data={'is_refund': True},
        )
        session |= create_session_with_single_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
        )
        session |= create_session_with_single_order(
            payment_method=[[self.cash_pm, {'amount': -11.2}]],
            products=[[self.product_12, {'qty': -1}]],
            extra_data={'is_refund': True},
        )
        payments = self.env['account.payment'].search(
            [('pos_session_id', 'in', session.ids)],
            order='id',
        )

        # Check bank payments in global entry
        expected_out_acc = self.bank_pm.outstanding_account_id
        destination_account = payments.destination_account_id
        outstanding_account = payments.outstanding_account_id
        self.assertEqual(len(payments), 2)
        self.assertEqual(destination_account, pos_receivable)           # Bank payment should be posted on the account defined on the payment method or default config account
        self.assertEqual(outstanding_account, expected_out_acc)
        self.assertEqual(payments.pos_payment_method_id, self.bank_pm)  # Only bank pm cash payment is managed from statements
        self.assertEqual(
            payments.mapped('payment_type'),
            ['inbound', 'outbound'],                                    # One sale and one refund
        )

        # Check cash payments
        lines = session.bank_statement_id.line_ids
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped('amount'), [11.2, -11.2])         # One line for the sale and one for the refund
        accounts = lines.invoice_line_ids.account_id.ids
        cash_acc = self.cash_pm.journal_id.default_account_id
        self.assertEqual(accounts, [cash_acc.id, pos_receivable.id])    # Cash payment should be posted on the cash account of the statement

        # Open session
        self.pos_config.open_ui()
        session = self.get_pos_session()
        cash_acc = self.pos_config._get_opening_balance()
        session.set_opening_control(cash_acc, "")
        order1 = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        refund1 = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
            extra_data={
                'is_refund': True,
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        order2 = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        refund2 = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -11.2}]],
            products=[[self.product_12, {'qty': -1}]],
            extra_data={
                'is_refund': True,
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )

        # Check bank payments for invoiced orders
        expected_out_acc = self.bank_pm.outstanding_account_id
        destination_account = payments.destination_account_id
        outstanding_account = payments.outstanding_account_id
        self.assertEqual(len(payments), 2)
        self.assertEqual(destination_account, pos_receivable)           # Bank payment should be posted on the account defined on the payment method or default config account
        self.assertEqual(outstanding_account, expected_out_acc)
        self.assertEqual(payments.pos_payment_method_id, self.bank_pm)  # Only bank pm cash payment is managed from statements
        self.assertEqual(
            payments.mapped('payment_type'),
            ['inbound', 'outbound'],                                    # One sale and one refund
        )

        sale_invoices = order1.account_move + order2.account_move
        refund_invoices = refund1.account_move + refund2.account_move
        partner_invoices = self.partner_1.invoice_ids.ids
        for id in sale_invoices.ids + refund_invoices.ids:
            self.assertIn(id, partner_invoices)

    def test_invoicing_zero_amount_pos_order(self):
        session = self.open_pos_session()
        self.product_6.lst_price = 0

        order = self.create_pos_order(
            payment_method=[
                [self.cash_pm, {'amount': 0}],
            ],
            products=[[self.product_6, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )

        session.close_session_from_ui({self.cash_pm.id: 0})
        self.assertEqual(session.state, 'closed')

        receivable = self.partner_1.property_account_receivable_id
        line_ids = order.account_move.line_ids
        self.assertEqual(len(line_ids), 2)                              # Only one line for the product
        self.assertEqual(line_ids[0].account_id, receivable)            # Line should be posted on the partner receivable
        self.assertEqual(line_ids[0].display_type, 'payment_term')
        self.assertEqual(line_ids[0].debit, 0)                          # Line should be at 0 since it's a zero amount order
        self.assertEqual(line_ids[0].credit, 0)                         # Line should be at 0 since it's a zero amount order

        # Check product line
        self.assertEqual(line_ids[1].display_type, 'product')
        self.assertEqual(line_ids[1].debit, 0)                          # Line should be at 0 since it's a zero amount order
        self.assertEqual(line_ids[1].credit, 0)                         # Line should be at 0 since it's a zero amount order

    def test_various_orders(self):
        StatementLine = self.env['account.bank.statement.line']
        BankPayment = self.env['account.payment']
        defaut_partner = self.pos_config.default_partner_id

        def create_order_and_check(order_args, values={
            'amount_total': 0,
            'amount_tax': 0,
            'amount_paid': 0,
        }):
            receivable = defaut_partner.property_account_receivable_id
            cash_acc = self.pos_config._get_opening_balance()
            session = self.open_pos_session(cash_acc)
            order = self.create_pos_order(**order_args)

            self.assertEqual(order.state, 'paid')
            self.assertEqual(order.amount_total, values['amount_total'])
            self.assertEqual(order.amount_tax, values['amount_tax'])
            self.assertEqual(order.amount_paid, values['amount_paid'])
            self.assertEqual(order.state, 'paid')
            self.assertEqual(session.state, 'opened')

            cash_pm = order.payment_ids.filtered(
                lambda pm: pm.payment_method_id.type == 'cash',
            )
            closing_amount = sum(cash_pm.mapped('amount')) + cash_acc
            session.close_session_from_ui({self.cash_pm.id: closing_amount})
            move = session.move_ids

            self.assertEqual(session.state, 'closed')
            self.assertEqual(order.state, 'done')

            if order.is_singly_invoiced and order.account_move:
                move = order.account_move
                partner = order.partner_id
                nb_product = len(order_args['products'])
                nb_payment = len(order_args['payment_method'])
                tax_ids = [p[0].taxes_id.ids for p in order_args['products']]
                flat = [x for xs in tax_ids for x in xs]
                nb_lines = nb_product + nb_payment + len(flat)
                self.assertEqual(move.state, 'posted')
                self.assertEqual(len(move.line_ids), nb_lines)
                self.assertEqual(move.amount_total, order.amount_total)
                self.assertEqual(move.amount_tax, order.amount_tax)

                if partner.property_account_receivable_id:
                    receivable = partner.property_account_receivable_id

            payment_term = move.line_ids.filtered(
                lambda line: line.display_type == 'payment_term',
            )
            zipped = zip(order.payment_ids, payment_term)
            for payment, term in zipped:
                pm = payment.payment_method_id

                if not order.to_invoice and pm.receivable_account_id:
                    receivable = pm.receivable_account_id

                if pm.type == 'cash':
                    self.assertEqual(term.account_id, receivable)
                    statement = StatementLine.search([
                        ('pos_session_id', '=', order.session_id.id),
                    ])
                    self.assertEqual(len(statement), 1)
                    self.assertEqual(statement.amount, payment.amount)
                elif pm.type == 'pay_later':
                    session_move = session.sales_move_id
                    self.assertEqual(order.to_invoice, True)
                    self.assertNotEqual(
                        order.account_move,
                        session_move,
                    )
                    acc = self.partner_1.property_account_receivable_id
                    self.assertEqual(term.account_id, acc)
                elif pm.type == 'bank':
                    payment = BankPayment.search([
                        ('pos_session_id', '=', order.session_id.id),
                    ])
                    self.assertEqual(term.account_id, receivable)
                    self.assertEqual(len(payment), 1)
                    self.assertEqual(payment.amount, term.debit)

        one_product_6_check_values = {
            'amount_total': 10.6,
            'amount_tax': 0.6,
            'amount_paid': 10.6,
        }
        create_order_and_check(
            order_args={
                'payment_method': [[self.customer_pm, {'amount': 10.6}]],
                'products': [[self.product_6, {}]],
                'extra_data': {'partner_id': self.partner_1.id},
            },
            values=one_product_6_check_values,
        )
        create_order_and_check(
            order_args={
                'payment_method': [[self.bank_pm, {'amount': 10.6}]],
                'products': [[self.product_6, {}]],
            },
            values=one_product_6_check_values,
        )
        create_order_and_check(
            order_args={
                'payment_method': [[self.cash_pm, {'amount': 10.6}]],
                'products': [[self.product_6, {}]],
            },
            values=one_product_6_check_values,
        )
        create_order_and_check(
            order_args={
                'payment_method': [
                    [self.cash_pm, {'amount': 5.3}],
                    [self.bank_pm, {'amount': 5.3}],
                ],
                'products': [[self.product_6, {}]],
            },
            values=one_product_6_check_values,
        )
        create_order_and_check(
            order_args={
                'payment_method': [
                    [self.bank_pm, {'amount': 2.3}],
                    [self.customer_pm, {'amount': 5.3}],
                    [self.cash_pm, {'amount': 3.0}],
                ],
                'products': [[self.product_6, {}]],
                'extra_data': {'partner_id': self.partner_1.id},
            },
            values=one_product_6_check_values,
        )
        total = 10.6 + 11.2 + 12.1
        create_order_and_check(
            order_args={
                'payment_method': [[self.bank_pm, {'amount': total}]],
                'products': [
                    [self.product_6, {}],
                    [self.product_12, {}],
                    [self.product_21, {}],
                ],
            },
            values={
                'amount_total': total,
                'amount_paid': total,
                'amount_tax': 0.6 + 1.2 + 2.1,
            },
        )
        total = 13.9
        create_order_and_check(
            order_args={
                'payment_method': [[self.bank_pm, {'amount': total}]],
                'products': [
                    [self.product_6_12_21, {}],
                ],
            },
            values={
                'amount_total': total,
                'amount_paid': total,
                'amount_tax': 0.6 + 1.2 + 2.1,
            },
        )
        self.tax_6.price_include_override = 'tax_included'
        create_order_and_check(
            order_args={
                'payment_method': [[self.bank_pm, {'amount': 10}]],
                'products': [[self.product_6, {}]],
            },
            values={
                'amount_total': 10,
                'amount_paid': 10,
                'amount_tax': 0.57,
            },
        )

    def test_pos_config_with_other_currency_than_company(self):
        eur = self.env.ref('base.EUR')
        usd = self.env.ref('base.USD')
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': usd.id,
        })

        self.pos_config.company_id.currency_id = eur
        self.pos_config.journal_id.currency_id = usd
        self.pos_config.currency_id = usd
        self.cash_pm.journal_id.currency_id = usd

        self.assertEqual(self.pos_config.company_id.currency_id, eur)
        self.assertEqual(self.pos_config.currency_id, usd)
        self.assertEqual(self.pos_config.journal_id.currency_id, usd)
        self.assertEqual(self.cash_pm.journal_id.currency_id, usd)

        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 21.8}]],          # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[[self.product_6, {}], [self.product_12, {}]],
        )

        self.assertEqual(order.amount_total, 21.8)
        self.assertEqual(order.amount_paid, 21.8)
        self.assertEqual(order.state, 'paid')
        self.close_session()

        self.assertTrue(session.move_ids)
        self.assertEqual(session.move_ids.currency_id, usd)

        total_usd = session.move_ids.amount_total_in_currency_signed
        total_eur = session.move_ids.amount_total_signed
        self.assertEqual(total_usd, 21.8)
        self.assertEqual(total_eur, 10.9)                               # 21.8 / 2 because of the rate we set on USD

        session = self.open_pos_session()
        invoiced_order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 21.8}]],          # Total amount of the order is 10 + 6% tax + 10 + 12% tax = 21.8
            products=[[self.product_6, {}], [self.product_12, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        move = invoiced_order.account_move
        self.assertEqual(move.currency_id, usd)
        total_usd = move.amount_total_in_currency_signed
        total_eur = move.amount_total_signed
        self.assertEqual(total_usd, 21.8)
        self.assertEqual(total_eur, 10.9)                               # 21.8 / 2 because of the rate we set on USD

    def test_accounting_items_when_closing_with_bank_difference(self):
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )
        self.assertEqual(order.state, 'paid')
        session.close_session_from_ui({self.bank_pm.id: 9.6})           # Simulate a bank difference of -1
        self.assertEqual(session.state, 'closed')

        move = session.correction_move_ids
        account_names = move.line_ids.mapped('account_id.name')
        balances = move.line_ids.mapped('balance')

        self.assertEqual(balances, [-1.0, 1.0])
        self.assertEqual(
            account_names,
            ['Accounts Receivable (PoS)', 'Cash Difference Loss'],
        )

        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.bank_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
        )
        self.assertEqual(order.state, 'paid')
        session.close_session_from_ui({self.bank_pm.id: 11.6})          # Simulate a bank difference of +1
        self.assertEqual(session.state, 'closed')

        move = session.correction_move_ids
        account_names = move.line_ids.mapped('account_id.name')
        balances = move.line_ids.mapped('balance')

        self.assertEqual(balances, [1.0, -1.0])
        self.assertEqual(
            account_names,
            ['Accounts Receivable (PoS)', 'Cash Difference Gain'],
        )

    def test_pos_order_with_closing_storno(self):
        with freeze_time('2020-01-01'):
            session = self.open_pos_session()
            order = self.create_pos_order(
                payment_method=[[self.bank_pm, {'amount': 10.6}]],
                products=[[self.product_6, {}]],
            )
            self.create_pos_order(
                payment_method=[[self.bank_pm, {'amount': -10.6}]],
                products=[[self.product_6, {'qty': -1}]],
                extra_data={
                    'is_refund': True,
                    'refunded_order_id': order.id,
                },
            )
            self.close_session()
            classic_refund = session.refunds_move_id
            classic_sale = session.sales_move_id

            self.env.company.account_storno = True
            session = self.open_pos_session()
            order = self.create_pos_order(
                payment_method=[[self.bank_pm, {'amount': 10.6}]],
                products=[[self.product_6, {}]],
            )
            self.create_pos_order(
                payment_method=[[self.bank_pm, {'amount': -10.6}]],
                products=[[self.product_6, {'qty': -1}]],
                extra_data={
                    'is_refund': True,
                    'refunded_order_id': order.id,
                },
            )
            self.close_session()
            storno_refund = session.refunds_move_id
            storno_sale = session.sales_move_id

            r_classic_credit = classic_refund.line_ids.mapped('credit')
            r_classic_debit = classic_refund.line_ids.mapped('debit')
            r_storno_credit = storno_refund.line_ids.mapped('credit')
            r_storno_debit = storno_refund.line_ids.mapped('debit')

            self.assertEqual(r_classic_credit, [10.6, 0.0, 0.0])
            self.assertEqual(r_classic_debit, [0.0, 10.0, 0.6])
            self.assertEqual(r_storno_credit, [0.0, -10.0, -0.6])
            self.assertEqual(r_storno_debit, [-10.6, 0.0, 0.0])

            s_classic_credit = classic_sale.line_ids.mapped('credit')
            s_classic_debit = classic_sale.line_ids.mapped('debit')
            s_storno_credit = storno_sale.line_ids.mapped('credit')
            s_storno_debit = storno_sale.line_ids.mapped('debit')

            self.assertEqual(s_classic_credit, s_storno_credit)
            self.assertEqual(s_classic_debit, s_storno_debit)

    def test_pos_order_session_closing_with_fp(self):
        """
        PoS orders can have fiscal positions applied on them. This test
        will check that when closing a session with orders with fiscal
        position, the correct taxes are applied and the correct accounts
        are used for the move lines of the session move.

        Will test to use the tax 21% with a fiscal position that
        replaces it with the tax 6%.

        Will also test with a product with tax of 12% with no
        destination tax (0%)
        """
        src_account = self.company.income_account_id
        dest_account = self.env['account.account'].search([
            ('company_ids', '=', self.company.id),
            ('account_type', '=', 'income'),
            ('id', '!=', src_account.id),
        ], limit=1)

        fp = self.env['account.fiscal.position'].create({
            'name': 'Test Fiscal Position',
        })
        account_fp = self.env['account.fiscal.position.account'].create({
            'position_id': fp.id,
            'account_src_id': src_account.id,
            'account_dest_id': dest_account.id,
        })
        fp.write({
            'account_ids': [(6, 0, account_fp.ids)],
        })
        self.tax_6.write({
            'fiscal_position_ids': [Command.link(fp.id)],
            'original_tax_ids': [Command.link(self.tax_21.id)],
        })
        self.env['account.tax'].create({
            'name': 'Tax 0%',
            'amount': 0,
            'fiscal_position_ids': [Command.link(fp.id)],
            'original_tax_ids': [Command.link(self.tax_12.id)],
        })

        # So when selling a product with 21% tax, the fiscal position
        # should replace it with the 6% tax
        session = self.open_pos_session()
        order_with_fp = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],          # Fiscal position apply 6% tax instead of 21% tax
            products=[[self.product_21, {}]],
            extra_data={
                'fiscal_position_id': fp.id,
            },
        )
        self.assertEqual(order_with_fp.amount_total, 10.6)
        self.assertEqual(order_with_fp.amount_tax, 0.6)
        self.assertEqual(order_with_fp.amount_paid, 10.6)
        self.assertEqual(order_with_fp.state, 'paid')

        order_without_fp = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 12.1}]],          # No fiscal position, so 21% tax should be applied
            products=[[self.product_21, {}]],
        )
        self.assertEqual(order_without_fp.amount_total, 12.1)
        self.assertEqual(order_without_fp.amount_tax, 2.1)
        self.assertEqual(order_without_fp.amount_paid, 12.1)
        self.assertEqual(order_without_fp.state, 'paid')

        order_with_0_tax = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10}]],            # Fiscal position applies 0% tax instead of 12% tax
            products=[[self.product_12, {}]],
            extra_data={
                'fiscal_position_id': fp.id,
            },
        )
        self.assertEqual(order_with_0_tax.amount_total, 10)
        self.assertEqual(order_with_0_tax.amount_tax, 0)
        self.assertEqual(order_with_0_tax.amount_paid, 10)
        self.assertEqual(order_with_0_tax.state, 'paid')
        self.close_session()
        move = session.move_ids
        product_line = move.line_ids.filtered(
            lambda line: line.display_type == 'product',
        )
        tax_lines = move.line_ids.filtered(
            lambda line: line.display_type == 'tax',
        )

        tax_sorted = tax_lines.sorted('balance')
        self.assertEqual(tax_sorted[0].balance, -2.1)
        self.assertEqual(tax_sorted[1].balance, -0.6)

        product_line_6 = product_line.filtered(
            lambda line: self.tax_6 in line.tax_ids,
        )
        product_line_21 = product_line.filtered(
            lambda line: self.tax_21 in line.tax_ids,
        )
        product_line_0 = product_line - product_line_6 - product_line_21
        self.assertEqual(product_line_6.account_id, dest_account)       # Product line with tax_6 should be posted on the dest account of the fiscal position
        self.assertEqual(product_line_21.account_id, src_account)       # Product line with tax_21 should be posted on the src account of the fiscal position
        self.assertEqual(product_line_0.account_id, dest_account)

    def test_pos_order_invoice_with_fp(self):
        src_account = self.company.income_account_id
        dest_account = self.env['account.account'].search([
            ('company_ids', '=', self.company.id),
            ('account_type', '=', 'income'),
            ('id', '!=', src_account.id),
        ], limit=1)

        fp = self.env['account.fiscal.position'].create({
            'name': 'Test Fiscal Position',
        })
        account_fp = self.env['account.fiscal.position.account'].create({
            'position_id': fp.id,
            'account_src_id': src_account.id,
            'account_dest_id': dest_account.id,
        })
        fp.write({
            'account_ids': [(6, 0, account_fp.ids)],
        })
        self.tax_6.write({
            'fiscal_position_ids': [Command.link(fp.id)],
            'original_tax_ids': [Command.link(self.tax_21.id)],
        })
        self.env['account.tax'].create({
            'name': 'Tax 0%',
            'amount': 0,
            'fiscal_position_ids': [Command.link(fp.id)],
            'original_tax_ids': [Command.link(self.tax_12.id)],
        })

        # So when selling a product with 21% tax, the fiscal position
        # should replace it with the 6% tax
        session = self.open_pos_session()
        order_with_fp = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],          # Fiscal position apply 6% tax instead of 21% tax
            products=[[self.product_21, {}]],
            extra_data={
                'fiscal_position_id': fp.id,
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertEqual(order_with_fp.amount_total, 10.6)
        self.assertEqual(order_with_fp.amount_tax, 0.6)
        self.assertEqual(order_with_fp.amount_paid, 10.6)
        self.assertEqual(order_with_fp.state, 'paid')
        self.assertEqual(order_with_fp.account_move.state, 'posted')
        move = order_with_fp.account_move
        self.assertEqual(move.fiscal_position_id, fp)

        order_without_fp = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 12.1}]],          # No fiscal position, so 21% tax should be applied
            products=[[self.product_21, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertEqual(order_without_fp.amount_total, 12.1)
        self.assertEqual(order_without_fp.amount_tax, 2.1)
        self.assertEqual(order_without_fp.amount_paid, 12.1)
        self.assertEqual(order_without_fp.state, 'paid')
        self.assertEqual(order_without_fp.account_move.state, 'posted')
        move = order_without_fp.account_move
        self.assertFalse(move.fiscal_position_id)

        order_with_0_tax = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10}]],            # Fiscal position applies 0% tax instead of 12% tax
            products=[[self.product_12, {}]],
            extra_data={
                'fiscal_position_id': fp.id,
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.assertEqual(order_with_0_tax.amount_total, 10)
        self.assertEqual(order_with_0_tax.amount_tax, 0)
        self.assertEqual(order_with_0_tax.amount_paid, 10)
        self.assertEqual(order_with_0_tax.state, 'paid')
        self.assertEqual(order_with_0_tax.account_move.state, 'posted')
        move = order_with_0_tax.account_move
        self.assertEqual(move.fiscal_position_id, fp)
        self.close_session()
        self.assertFalse(session.move_ids)

    def test_pos_order_with_company_branch(self):
        branch = self.env['res.company'].create({
            'name': 'Sub Company',
            'parent_id': self.env.company.id,
            'chart_template': self.env.company.chart_template,
            'country_id': self.env.company.country_id.id,
        })
        self.env.cr.precommit.run()

        AccJournal = self.env['account.journal'].with_company(branch)
        PosPm = self.env['pos.payment.method'].with_company(branch)
        PosConfig = self.env['pos.config'].with_company(branch)

        cash_journal = AccJournal.create({
            'name': 'Cash Test',
            'type': 'cash',
            'company_id': branch.id,
            'code': 'CSH',
            'sequence': 10,
        })
        cash_pm = PosPm.create({
            'name': 'Bank',
            'type': 'cash',
            'journal_id': cash_journal.id,
        })
        self.pos_config = PosConfig.create({
            'name': 'Main - Sub Company',
            'journal_id': self.company_data['default_journal_sale'].id,
            'payment_method_ids': [(4, cash_pm.id)],
        })

        self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.close_session()
        self.assertEqual(order.config_id, self.pos_config)

    def test_pos_order_rounding_two_payment_methods(self):
        """
        This test check the cash rounding is correctly applied when
        there is multiple payment methods on the order.
        Invoicing orders shouldn't raise any traceback.
        """
        self.product_21.lst_price = 6  # Was tested in the UI with this price and it crashes
        self.rounding_method.rounding_method = 'HALF-UP'
        self.pos_config.write({
            'cash_rounding': True,
            'rounding_method': self.rounding_method.id,
            'only_round_cash_method': True,
        })
        self.open_pos_session()
        self.create_pos_order(
            payment_method=[
                [self.cash_pm, {'amount': 5}],
                [self.bank_pm, {'amount': 2.26}],
            ],
            products=[[self.product_21, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.create_pos_order(
            payment_method=[
                [self.bank_pm, {'amount': 5}],
                [self.cash_pm, {'amount': 2.25}],
            ],
            products=[[self.product_21, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.close_session()

    def test_cash_destination_account(self):
        session = self.open_pos_session()
        session_dest = session._get_receivable_account()
        cash_profit_dest = self.cash_pm.journal_id.profit_account_id
        cash_loss_dest = self.cash_pm.journal_id.loss_account_id
        cash_suspense_dest = self.cash_pm.journal_id.suspense_account_id
        cash_default_dest = self.cash_pm.journal_id.default_account_id
        partner_dest = self.partner_1.property_account_receivable_id

        partner_order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        account_move_lines = partner_order.account_move.line_ids
        payment_line = account_move_lines.filtered_domain([
            ('display_type', '=', 'payment_term'),
        ])
        self.assertEqual(payment_line.account_id, partner_dest)
        self.assertEqual(
            payment_line.reconciled_lines_ids.statement_id,
            session.bank_statement_id,
        )

        session.try_cash_in_out('out', 10, '10 Out', False)
        out_line = session.bank_statement_id.line_ids[-1]
        session.try_cash_in_out('in', 10, '10 In', False)
        in_line = session.bank_statement_id.line_ids[-1]
        out_accounts = out_line.line_ids.account_id
        in_accounts = in_line.line_ids.account_id
        self.assertEqual(out_accounts[0], cash_default_dest)
        self.assertEqual(out_accounts[1], cash_suspense_dest)
        self.assertEqual(in_accounts[0], cash_default_dest)
        self.assertEqual(in_accounts[1], cash_suspense_dest)

        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
        )
        self.close_session()
        account_move = order.account_move
        payment_line = account_move.line_ids.filtered_domain([
            ('display_type', '=', 'payment_term'),
        ])
        self.assertEqual(payment_line.account_id, session_dest)
        last_closing = self.env['pos.session'].search(
            [], limit=1, order="id desc",
        ).closing_balance

        cash_pm = self.pos_config._get_cash_payment_method()
        cash_pm.journal_id._compute_current_statement_balance()         # Force recompute in tests.
        session = self.open_pos_session(last_closing - 10)
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 11.2}]],
            products=[[self.product_12, {}]],
        )
        closing_data = session.get_closing_control_data()
        cash_details = closing_data['default_cash_details']
        expected_cashbox_amount = cash_details['payment_amount'] + 100
        self.close_session(expected_cashbox_amount)
        statement_lines = session.bank_statement_id.line_ids
        opening_statement = statement_lines[0]
        order_statement = statement_lines[1]
        closing_statement = statement_lines[2]
        self.assertEqual(
            opening_statement.line_ids[0].account_id,
            cash_default_dest,
        )
        self.assertEqual(
            opening_statement.line_ids[1].account_id,
            cash_loss_dest,
        )
        self.assertEqual(
            order_statement.line_ids[0].account_id,
            cash_default_dest,
        )
        self.assertEqual(
            order_statement.line_ids[1].account_id,
            session_dest,
        )
        self.assertEqual(
            closing_statement.line_ids[0].account_id,
            cash_default_dest,
        )
        self.assertEqual(
            closing_statement.line_ids[1].account_id,
            cash_profit_dest,
        )

    def test_fake_refund_order_closing(self):
        session = self.open_pos_session()
        order = self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
            extra_data={
                'partner_id': self.partner_1.id,
                'to_invoice': True,
            },
        )
        self.close_session()
        self.assertFalse(session.refunds_move_id)
        self.assertFalse(session.sales_move_id)
        self.assertEqual(order.account_move.move_type, 'out_refund')

        session = self.open_pos_session()
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
        )
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': -10.6}]],
            products=[[self.product_6, {'qty': -1}]],
        )
        self.create_pos_order(
            payment_method=[[self.cash_pm, {'amount': 10.6}]],
            products=[[self.product_6, {'qty': 1}]],
        )
        self.close_session()
        self.assertTrue(session.refunds_move_id)
        self.assertTrue(session.sales_move_id)
        self.assertEqual(session.refunds_move_id.move_type, 'out_refund')
        self.assertEqual(session.sales_move_id.move_type, 'out_invoice')
        self.assertEqual(session.refunds_move_id.amount_total, 21.2)
        self.assertEqual(session.sales_move_id.amount_total, 10.6)
