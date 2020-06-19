# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

import odoo
from odoo import fields, tools
from odoo.tools import float_compare, mute_logger, test_reports
from odoo.tests.common import Form
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleCommon):


    def test_order_refund(self):
        self.pos_config.open_session_cb(check_coa=False)
        current_session = self.pos_config.current_session_id
        # I create a new PoS order with 2 lines
        order = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 2.0,
                'tax_ids': [(6, 0, self.product3.taxes_id.ids)],
                'price_subtotal': 450 * (1 - 5/100.0) * 2,
                'price_subtotal_incl': 450 * (1 - 5/100.0) * 2,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 5.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.ids)],
                'price_subtotal': 300 * (1 - 5/100.0) * 3,
                'price_subtotal_incl': 300 * (1 - 5/100.0) * 3,
            })],
            'amount_total': 1710.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.assertAlmostEqual(order.amount_total, order.amount_paid, msg='Order should be fully paid.')

        # I create a refund
        refund_action = order.refund()
        refund = self.PosOrder.browse(refund_action['res_id'])

        self.assertEqual(order.amount_total, -1*refund.amount_total,
            "The refund does not cancel the order (%s and %s)" % (order.amount_total, refund.amount_total))

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # I click on the validate button to register the payment.
        refund_payment.with_context(**payment_context).check()

        self.assertEqual(refund.state, 'paid', "The refund is not marked as paid")
        self.assertTrue(refund.payment_ids.payment_method_id.is_cash_count, msg='There should only be one payment and paid in cash.')

        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed', msg='State of current session should be closed.')

    def test_order_refund_lots(self):
        # open pos session
        self.pos_config.open_session_cb()
        current_session = self.pos_config.current_session_id

        # set up product iwith SN tracing and create two lots (1001, 1002)
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.product2 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        inventory = self.env['stock.inventory'].create({
            'name': 'add product2',
            'location_ids': [(4, self.stock_location.id)],
            'product_ids': [(4, self.product2.id)],
        })
        inventory.action_start()

        lot1 = self.env['stock.production.lot'].create({
            'name': '1001',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.production.lot'].create({
            'name': '1002',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.inventory.line'].create([
            {
            'inventory_id': inventory.id,
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'prod_lot_id': lot1.id,
            'product_qty': 1
            },
            {
            'inventory_id': inventory.id,
            'location_id': self.stock_location.id,
            'product_id': self.product2.id,
            'prod_lot_id': lot2.id,
            'product_qty': 1
            },
        ])

        inventory.action_validate()

        # create pos order with the two SN created before

        order = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'id': 1,
                'product_id': self.product2.id,
                'price_unit': 6,
                'discount': 0,
                'qty': 2,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 12,
                'price_subtotal_incl': 12,
                'pack_lot_ids': [
                    [0, 0, {'lot_name': '1001'}],
                    [0, 0, {'lot_name': '1002'}],
                ]
            })],
            'pricelist_id': 1,
            'amount_paid': 12.0,
            'amount_total': 12.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': False,
            })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        # I create a refund
        refund_action = order.refund()
        refund = self.PosOrder.browse(refund_action['res_id'])

        order_lot_id = [lot_id.lot_name for lot_id in order.lines.pack_lot_ids]
        refund_lot_id = [lot_id.lot_name for lot_id in refund.lines.pack_lot_ids]
        self.assertEqual(
            order_lot_id,
            refund_lot_id,
            "In the refund we should find the same lot as in the original order")

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # I click on the validate button to register the payment.
        refund_payment.with_context(**payment_context).check()

        self.assertEqual(refund.state, 'paid', "The refund is not marked as paid")
        current_session.action_pos_session_closing_control()

    def test_order_to_picking(self):
        """
            In order to test the Point of Sale in module, I will do three orders from the sale to the payment,
            invoicing + picking, but will only check the picking consistency in the end.

            TODO: Check the negative picking after changing the picking relation to One2many (also for a mixed use case),
            check the quantity, the locations and return picking logic
        """

        def compute_tax(product, price, qty=1, taxes=None):
            if taxes is None:
                taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.user.id)
            currency = self.pos_config.pricelist_id.currency_id
            res = taxes.compute_all(price, currency, qty, product=product)
            untax = res['total_excluded']
            return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

        # I click on create a new session button
        self.pos_config.open_session_cb(check_coa=False)
        current_session = self.pos_config.current_session_id

        # I create a PoS order with 2 units of PCSC234 at 450 EUR
        # and 3 units of PCSC349 at 300 EUR.
        untax1, atax1 = compute_tax(self.product3, 450, 2)
        untax2, atax2 = compute_tax(self.product4, 300, 3)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 0.0,
                'qty': 2.0,
                'tax_ids': [(6, 0, self.product3.taxes_id.ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 0.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.ids)],
                'price_subtotal': untax2,
                'price_subtotal_incl': untax2 + atax2,
            })],
            'amount_tax': atax1 + atax2,
            'amount_total': untax1 + untax2 + atax1 + atax2,
            'amount_paid': 0,
            'amount_return': 0,
        })

        context_make_payment = {
            "active_ids": [self.pos_order_pos1.id],
            "active_id": self.pos_order_pos1.id
        }
        self.pos_make_payment_2 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': untax1 + untax2 + atax1 + atax2
        })

        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos1.id}

        self.pos_make_payment_2.with_context(context_payment).check()
        # I check that the order is marked as paid
        self.assertEqual(
            self.pos_order_pos1.state,
            'paid',
            'Order should be in paid state.'
        )

        # I test that the pickings are created as expected during payment
        # One picking attached and having all the positive move lines in the correct state
        self.assertEqual(
            self.pos_order_pos1.picking_ids[0].state,
            'done',
            'Picking should be in done state.'
        )
        self.assertEqual(
            self.pos_order_pos1.picking_ids[0].move_lines.mapped('state'),
            ['done', 'done'],
            'Move Lines should be in done state.'
        )

        # I create a second order
        untax1, atax1 = compute_tax(self.product3, 450, -2)
        untax2, atax2 = compute_tax(self.product4, 300, -3)
        self.pos_order_pos2 = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0003",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 0.0,
                'qty': (-2.0),
                'tax_ids': [(6, 0, self.product3.taxes_id.ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0004",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 0.0,
                'qty': (-3.0),
                'tax_ids': [(6, 0, self.product4.taxes_id.ids)],
                'price_subtotal': untax2,
                'price_subtotal_incl': untax2 + atax2,
            })],
            'amount_tax': atax1 + atax2,
            'amount_total': untax1 + untax2 + atax1 + atax2,
            'amount_paid': 0,
            'amount_return': 0,
        })

        context_make_payment = {
            "active_ids": [self.pos_order_pos2.id],
            "active_id": self.pos_order_pos2.id
        }
        self.pos_make_payment_3 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': untax1 + untax2 + atax1 + atax2
        })

        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos2.id}
        self.pos_make_payment_3.with_context(context_payment).check()

        # I check that the order is marked as paid
        self.assertEqual(
            self.pos_order_pos2.state,
            'paid',
            'Order should be in paid state.'
        )

        # I test that the pickings are created as expected
        # One picking attached and having all the positive move lines in the correct state
        self.assertEqual(
            self.pos_order_pos2.picking_ids[0].state,
            'done',
            'Picking should be in done state.'
        )
        self.assertEqual(
            self.pos_order_pos2.picking_ids[0].move_lines.mapped('state'),
            ['done', 'done'],
            'Move Lines should be in done state.'
        )

        untax1, atax1 = compute_tax(self.product3, 450, -2)
        untax2, atax2 = compute_tax(self.product4, 300, 3)
        self.pos_order_pos3 = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0005",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 0.0,
                'qty': (-2.0),
                'tax_ids': [(6, 0, self.product3.taxes_id.ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0006",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 0.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.ids)],
                'price_subtotal': untax2,
                'price_subtotal_incl': untax2 + atax2,
            })],
            'amount_tax': atax1 + atax2,
            'amount_total': untax1 + untax2 + atax1 + atax2,
            'amount_paid': 0,
            'amount_return': 0,
        })

        context_make_payment = {
            "active_ids": [self.pos_order_pos3.id],
            "active_id": self.pos_order_pos3.id
        }
        self.pos_make_payment_4 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': untax1 + untax2 + atax1 + atax2,
        })

        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos3.id}
        self.pos_make_payment_4.with_context(context_payment).check()

        # I check that the order is marked as paid
        self.assertEqual(
            self.pos_order_pos3.state,
            'paid',
            'Order should be in paid state.'
        )

        # I test that the pickings are created as expected
        # One picking attached and having all the positive move lines in the correct state
        self.assertEqual(
            self.pos_order_pos3.picking_ids[0].state,
            'done',
            'Picking should be in done state.'
        )
        self.assertEqual(
            self.pos_order_pos3.picking_ids[0].move_lines.mapped('state'),
            ['done'],
            'Move Lines should be in done state.'
        )
        # I close the session to generate the journal entries
        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_order_to_invoice(self):

        def compute_tax(product, price, qty=1, taxes=None):
            if taxes is None:
                taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.user.id)
            currency = self.pos_config.pricelist_id.currency_id
            res = taxes.compute_all(price, currency, qty, product=product)
            untax = res['total_excluded']
            return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

        self.pos_config.open_session_cb(check_coa=False)
        current_session = self.pos_config.current_session_id

        untax1, atax1 = compute_tax(self.product3, 450*0.95, 2)
        untax2, atax2 = compute_tax(self.product4, 300*0.95, 3)
        # I create a new PoS order with 2 units of PC1 at 450 EUR (Tax Incl) and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 2.0,
                'tax_ids': [(6, 0, self.product3.taxes_id.filtered(lambda t: t.company_id.id == self.company_id).ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 5.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.filtered(lambda t: t.company_id.id == self.company_id).ids)],
                'price_subtotal': untax2,
                'price_subtotal_incl': untax2 + atax2,
            })],
            'amount_tax': atax1 + atax2,
            'amount_total': untax1 + untax2 + atax1 + atax2,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # I click on the "Make Payment" wizard to pay the PoS order
        context_make_payment = {"active_ids": [self.pos_order_pos1.id], "active_id": self.pos_order_pos1.id}
        self.pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': untax1 + untax2 + atax1 + atax2,
        })
        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos1.id}
        self.pos_make_payment.with_context(context_payment).check()

        # I check that the order is marked as paid and there is no invoice
        # attached to it
        self.assertEqual(self.pos_order_pos1.state, 'paid', "Order should be in paid state.")
        self.assertFalse(self.pos_order_pos1.account_move, 'Invoice should not be attached to order.')

        # I generate an invoice from the order
        res = self.pos_order_pos1.action_pos_order_invoice()
        self.assertIn('res_id', res, "Invoice should be created")

        # I test that the total of the attached invoice is correct
        invoice = self.env['account.move'].browse(res['res_id'])
        invoice.post()
        self.assertAlmostEqual(
            invoice.amount_total, self.pos_order_pos1.amount_total, places=2, msg="Invoice not correct")

        # I close the session to generate the journal entries
        current_session.action_pos_session_closing_control()

        """In order to test the reports on Bank Statement defined in point_of_sale module, I create a bank statement line, confirm it and print the reports"""

        # I select the period and journal for the bank statement

        context_journal = {'journal_type': 'bank'}
        self.assertTrue(self.AccountBankStatement.with_context(
            context_journal)._default_journal(), 'Journal has not been selected')
        journal = self.env['account.journal'].create({
            'name': 'Bank Test',
            'code': 'BNKT',
            'type': 'bank',
            'company_id': self.company_id,
        })
        # I create a bank statement with Opening and Closing balance 0.
        account_statement = self.AccountBankStatement.create({
            'balance_start': 0.0,
            'balance_end_real': 0.0,
            'date': time.strftime('%Y-%m-%d'),
            'journal_id': journal.id,
            'company_id': self.company_id,
            'name': 'pos session test',
        })
        # I create bank statement line
        account_statement_line = self.AccountBankStatementLine.create({
            'amount': 1000,
            'partner_id': self.partner4.id,
            'statement_id': account_statement.id,
            'payment_ref': 'EXT001'
        })
        # I modify the bank statement and set the Closing Balance.
        account_statement.write({
            'balance_end_real': 1000.0,
        })

        # I reconcile the bank statement.
        new_aml_dicts = [{
            'account_id': self.partner4.property_account_receivable_id.id,
            'name': "EXT001",
            'credit': 1000.0,
            'debit': 0.0,
        }]

        # I confirm the bank statement using Confirm button

        self.AccountBankStatement.button_validate()

    def test_create_from_ui(self):
        """
        Simulation of sales coming from the interface, even after closing the session
        """

        def compute_tax(product, price, qty=1, taxes=None):
            if not taxes:
                taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.user.id)
            currency = self.pos_config.pricelist_id.currency_id
            res = taxes.compute_all(price, currency, qty, product=product)
            untax = res['total_excluded']
            return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

        # I click on create a new session button
        self.pos_config.open_session_cb(check_coa=False)

        current_session = self.pos_config.current_session_id
        num_starting_orders = len(current_session.order_ids)

        untax, atax = compute_tax(self.led_lamp, 0.9)
        carrot_order = {'data':
          {'amount_paid': untax + atax,
           'amount_return': 0,
           'amount_tax': atax,
           'amount_total': untax + atax,
           'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'id': 42,
              'pack_lot_ids': [],
              'price_unit': 0.9,
              'product_id': self.led_lamp.id,
              'price_subtotal': 0.9,
              'price_subtotal_incl': 1.04,
              'qty': 1,
              'tax_ids': [(6, 0, self.led_lamp.taxes_id.ids)]}]],
           'name': 'Order 00042-003-0014',
           'partner_id': False,
           'pos_session_id': current_session.id,
           'sequence_number': 2,
           'statement_ids': [[0,
             0,
             {'amount': untax + atax,
              'name': fields.Datetime.now(),
              'payment_method_id': self.cash_payment_method.id}]],
           'uid': '00042-003-0014',
           'user_id': self.env.uid},
          'id': '00042-003-0014',
          'to_invoice': False}

        untax, atax = compute_tax(self.whiteboard_pen, 1.2)
        zucchini_order = {'data':
          {'amount_paid': untax + atax,
           'amount_return': 0,
           'amount_tax': atax,
           'amount_total': untax + atax,
           'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'id': 3,
              'pack_lot_ids': [],
              'price_unit': 1.2,
              'product_id': self.whiteboard_pen.id,
              'price_subtotal': 1.2,
              'price_subtotal_incl': 1.38,
              'qty': 1,
              'tax_ids': [(6, 0, self.whiteboard_pen.taxes_id.ids)]}]],
           'name': 'Order 00043-003-0014',
           'partner_id': False,
           'pos_session_id': current_session.id,
           'sequence_number': self.pos_config.journal_id.id,
           'statement_ids': [[0,
             0,
             {'amount': untax + atax,
              'name': fields.Datetime.now(),
              'payment_method_id': self.credit_payment_method.id}]],
           'uid': '00043-003-0014',
           'user_id': self.env.uid},
          'id': '00043-003-0014',
          'to_invoice': False}

        untax, atax = compute_tax(self.newspaper_rack, 1.28)
        newspaper_rack_order = {'data':
          {'amount_paid': untax + atax,
           'amount_return': 0,
           'amount_tax': atax,
           'amount_total': untax + atax,
           'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
           'lines': [[0,
             0,
             {'discount': 0,
              'id': 3,
              'pack_lot_ids': [],
              'price_unit': 1.28,
              'product_id': self.newspaper_rack.id,
              'price_subtotal': 1.28,
              'price_subtotal_incl': 1.47,
              'qty': 1,
              'tax_ids': [[6, False, self.newspaper_rack.taxes_id.ids]]}]],
           'name': 'Order 00044-003-0014',
           'partner_id': False,
           'pos_session_id': current_session.id,
           'sequence_number': self.pos_config.journal_id.id,
           'statement_ids': [[0,
             0,
             {'amount': untax + atax,
              'name': fields.Datetime.now(),
              'payment_method_id': self.bank_payment_method.id}]],
           'uid': '00044-003-0014',
           'user_id': self.env.uid},
          'id': '00044-003-0014',
          'to_invoice': False}

        # I create an order on an open session
        self.PosOrder.create_from_ui([carrot_order])
        self.assertEqual(num_starting_orders + 1, len(current_session.order_ids), "Submitted order not encoded")

        # I close the session
        current_session.action_pos_session_closing_control()
        self.assertEqual(current_session.state, 'closed', "Session was not properly closed")
        self.assertFalse(self.pos_config.current_session_id, "Current session not properly recomputed")

        # I keep selling after the session is closed
        with mute_logger('odoo.addons.point_of_sale.models.pos_order'):
            self.PosOrder.create_from_ui([zucchini_order, newspaper_rack_order])
        rescue_session = self.PosSession.search([
            ('config_id', '=', self.pos_config.id),
            ('state', '=', 'opened'),
            ('rescue', '=', True)
        ])
        self.assertEqual(len(rescue_session), 1, "One (and only one) rescue session should be created for orphan orders")
        self.assertIn("(RESCUE FOR %s)" % current_session.name, rescue_session.name, "Rescue session is not linked to the previous one")
        self.assertEqual(len(rescue_session.order_ids), 2, "Rescue session does not contain both orders")

        # I close the rescue session
        rescue_session.action_pos_session_closing_control()
        self.assertEqual(rescue_session.state, 'closed', "Rescue session was not properly closed")

    def test_order_to_payment_currency(self):
        """
            In order to test the Point of Sale in module, I will do a full flow from the sale to the payment and invoicing.
            I will use two products, one with price including a 10% tax, the other one with 5% tax excluded from the price.
            The order will be in a different currency than the company currency.
        """
        # Make sure the company is in USD
        self.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            [self.env.ref('base.USD').id, self.env.company.id])

        # Demo data are crappy, clean-up the rates
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': '2010-01-01',
            'rate': 2.0,
            'currency_id': self.env.ref('base.EUR').id,
        })

        def compute_tax(product, price, qty=1, taxes=None):
            if not taxes:
                taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.user.id)
            currency = self.pos_config.pricelist_id.currency_id
            res = taxes.compute_all(price, currency, qty, product=product)
            untax = res['total_excluded']
            return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

        # make a config that has currency different from the company
        eur_pricelist = self.partner1.property_product_pricelist.copy(default={'currency_id': self.env.ref('base.EUR').id})
        sale_journal = self.env['account.journal'].create({
            'name': 'PoS Sale EUR',
            'type': 'sale',
            'code': 'POSE',
            'company_id': self.company.id,
            'sequence': 12,
            'currency_id': self.env.ref('base.EUR').id
        })
        eur_config = self.pos_config.create({
            'name': 'Shop EUR Test',
            'module_account': False,
            'journal_id': sale_journal.id,
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, eur_pricelist.ids)],
            'pricelist_id': eur_pricelist.id,
            'payment_method_ids': [(6, 0, self.bank_payment_method.ids)]
        })

        # I click on create a new session button
        eur_config.open_session_cb(check_coa=False)
        current_session = eur_config.current_session_id

        # I create a PoS order with 2 units of PCSC234 at 450 EUR (Tax Incl)
        # and 3 units of PCSC349 at 300 EUR. (Tax Excl)

        untax1, atax1 = compute_tax(self.product3, 450, 2)
        untax2, atax2 = compute_tax(self.product4, 300, 3)
        self.pos_order_pos0 = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'pricelist_id': eur_pricelist.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 0.0,
                'qty': 2.0,
                'tax_ids': [(6, 0, self.product3.taxes_id.ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 0.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.ids)],
                'price_subtotal': untax2,
                'price_subtotal_incl': untax2 + atax2,
            })],
            'amount_tax': atax1 + atax2,
            'amount_total': untax1 + untax2 + atax1 + atax2,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # I check that the total of the order is now equal to (450*2 +
        # 300*3*1.05)*0.95
        self.assertLess(
            abs(self.pos_order_pos0.amount_total - (450 * 2 + 300 * 3 * 1.05)),
            0.01, 'The order has a wrong total including tax and discounts')

        # I click on the "Make Payment" wizard to pay the PoS order with a
        # partial amount of 100.0 EUR
        context_make_payment = {"active_ids": [self.pos_order_pos0.id], "active_id": self.pos_order_pos0.id}
        self.pos_make_payment_0 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': 100.0,
            'payment_method_id': self.bank_payment_method.id,
        })

        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos0.id}
        self.pos_make_payment_0.with_context(context_payment).check()

        # I check that the order is not marked as paid yet
        self.assertEqual(self.pos_order_pos0.state, 'draft', 'Order should be in draft state.')

        # On the second payment proposition, I check that it proposes me the
        # remaining balance which is 1790.0 EUR
        defs = self.pos_make_payment_0.with_context({'active_id': self.pos_order_pos0.id}).default_get(['amount'])

        self.assertLess(
            abs(defs['amount'] - ((450 * 2 + 300 * 3 * 1.05) - 100.0)), 0.01, "The remaining balance is incorrect.")

        #'I pay the remaining balance.
        context_make_payment = {
            "active_ids": [self.pos_order_pos0.id], "active_id": self.pos_order_pos0.id}

        self.pos_make_payment_1 = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': (450 * 2 + 300 * 3 * 1.05) - 100.0,
            'payment_method_id': self.bank_payment_method.id,
        })

        # I click on the validate button to register the payment.
        self.pos_make_payment_1.with_context(context_make_payment).check()

        # I check that the order is marked as paid
        self.assertEqual(self.pos_order_pos0.state, 'paid', 'Order should be in paid state.')

        # I generate the journal entries
        current_session.action_pos_session_validate()

        # I test that the generated journal entry is attached to the PoS order
        self.assertTrue(current_session.move_id, "Journal entry should have been attached to the session.")

        # Check the amounts
        debit_lines = current_session.move_id.mapped('line_ids.debit')
        credit_lines = current_session.move_id.mapped('line_ids.credit')
        amount_currency_lines = current_session.move_id.mapped('line_ids.amount_currency')
        for a, b in zip(sorted(debit_lines), [0.0, 0.0, 0.0, 0.0, 922.5]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(sorted(credit_lines), [0.0, 22.5, 40.91, 409.09, 450]):
            self.assertAlmostEqual(a, b)
        for a, b in zip(sorted(amount_currency_lines), [-900, -818.18, -81.82, -45, 1845]):
            self.assertAlmostEqual(a, b)

    def test_order_to_invoice_no_tax(self):
        self.pos_config.open_session_cb(check_coa=False)
        current_session = self.pos_config.current_session_id

        # I create a new PoS order with 2 units of PC1 at 450 EUR (Tax Incl) and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.company_id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 2.0,
                'price_subtotal': 855,
                'price_subtotal_incl': 855,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 5.0,
                'qty': 3.0,
                'price_subtotal': 855,
                'price_subtotal_incl': 855,
            })],
            'amount_tax': 855 * 2,
            'amount_total': 855 * 2,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        # I click on the "Make Payment" wizard to pay the PoS order
        context_make_payment = {"active_ids": [self.pos_order_pos1.id], "active_id": self.pos_order_pos1.id}
        self.pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': 855 * 2,
        })
        # I click on the validate button to register the payment.
        context_payment = {'active_id': self.pos_order_pos1.id}
        self.pos_make_payment.with_context(context_payment).check()

        # I check that the order is marked as paid and there is no invoice
        # attached to it
        self.assertEqual(self.pos_order_pos1.state, 'paid', "Order should be in paid state.")
        self.assertFalse(self.pos_order_pos1.account_move, 'Invoice should not be attached to order yet.')

        # I generate an invoice from the order
        res = self.pos_order_pos1.action_pos_order_invoice()
        self.assertIn('res_id', res, "No invoice created")

        # I test that the total of the attached invoice is correct
        invoice = self.env['account.move'].browse(res['res_id'])
        invoice.post()
        self.assertAlmostEqual(
            invoice.amount_total, self.pos_order_pos1.amount_total, places=2, msg="Invoice not correct")

        for iline in invoice.invoice_line_ids:
            self.assertFalse(iline.tax_ids)

        self.pos_config.current_session_id.action_pos_session_closing_control()
