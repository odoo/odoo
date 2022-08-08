# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from freezegun import freeze_time

import odoo
from odoo import fields, tools
from odoo.tools import float_compare, mute_logger, test_reports
from odoo.tests.common import Form
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleCommon):

    def compute_tax(self, product, price, qty=1, taxes=None):
        if not taxes:
            taxes = product.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id)
        currency = self.pos_config.pricelist_id.currency_id
        res = taxes.compute_all(price, currency, qty, product=product)
        untax = res['total_excluded']
        return untax, sum(tax.get('amount', 0.0) for tax in res['taxes'])

    def test_order_refund(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        # I create a new PoS order with 2 lines
        order = self.PosOrder.create({
            'company_id': self.env.company.id,
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

        total_cash_payment = sum(current_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        current_session.post_closing_cash_details(total_cash_payment)
        current_session.close_session_from_ui()
        self.assertEqual(current_session.state, 'closed', msg='State of current session should be closed.')

    def test_order_refund_lots(self):
        # open pos session
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # set up product iwith SN tracing and create two lots (1001, 1002)
        self.stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.product2 = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        lot1 = self.env['stock.lot'].create({
            'name': '1001',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })
        lot2 = self.env['stock.lot'].create({
            'name': '1002',
            'product_id': self.product2.id,
            'company_id': self.env.company.id,
        })

        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'inventory_quantity': 1,
            'location_id': self.stock_location.id,
            'lot_id': lot1.id
        }).action_apply_inventory()
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': self.product2.id,
            'inventory_quantity': 1,
            'location_id': self.stock_location.id,
            'lot_id': lot2.id
        }).action_apply_inventory()

        # create pos order with the two SN created before

        order = self.PosOrder.create({
            'company_id': self.env.company.id,
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

        # I click on create a new session button
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # I create a PoS order with 2 units of PCSC234 at 450 EUR
        # and 3 units of PCSC349 at 300 EUR.
        untax1, atax1 = self.compute_tax(self.product3, 450, 2)
        untax2, atax2 = self.compute_tax(self.product4, 300, 3)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.env.company.id,
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
            self.pos_order_pos1.picking_ids[0].move_ids.mapped('state'),
            ['done', 'done'],
            'Move Lines should be in done state.'
        )

        # I create a second order
        untax1, atax1 = self.compute_tax(self.product3, 450, -2)
        untax2, atax2 = self.compute_tax(self.product4, 300, -3)
        self.pos_order_pos2 = self.PosOrder.create({
            'company_id': self.env.company.id,
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
            self.pos_order_pos2.picking_ids[0].move_ids.mapped('state'),
            ['done', 'done'],
            'Move Lines should be in done state.'
        )

        untax1, atax1 = self.compute_tax(self.product3, 450, -2)
        untax2, atax2 = self.compute_tax(self.product4, 300, 3)
        self.pos_order_pos3 = self.PosOrder.create({
            'company_id': self.env.company.id,
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
            self.pos_order_pos3.picking_ids[0].move_ids.mapped('state'),
            ['done'],
            'Move Lines should be in done state.'
        )
        # I close the session to generate the journal entries
        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_order_to_picking02(self):
        """ This test is similar to test_order_to_picking except that this time, there are two products:
            - One tracked by lot
            - One untracked
            - Both are in a sublocation of the main warehouse
        """
        tracked_product, untracked_product = self.env['product.product'].create([{
            'name': 'SuperProduct Tracked',
            'type': 'product',
            'tracking': 'lot',
            'available_in_pos': True,
        }, {
            'name': 'SuperProduct Untracked',
            'type': 'product',
            'available_in_pos': True,
        }])
        wh_location = self.company_data['default_warehouse'].lot_stock_id
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': wh_location.id,
        })
        lot = self.env['stock.lot'].create({
            'name': 'SuperLot',
            'product_id': tracked_product.id,
            'company_id': self.env.company.id,
        })
        qty = 2
        self.env['stock.quant']._update_available_quantity(tracked_product, shelf1_location, qty, lot_id=lot)
        self.env['stock.quant']._update_available_quantity(untracked_product, shelf1_location, qty)

        self.pos_config.open_ui()
        self.pos_config.current_session_id.update_stock_at_closing = False

        untax, atax = self.compute_tax(tracked_product, 1.15, 1)

        for dummy in range(qty):
            pos_order = self.PosOrder.create({
                'company_id': self.env.company.id,
                'session_id': self.pos_config.current_session_id.id,
                'pricelist_id': self.partner1.property_product_pricelist.id,
                'partner_id': self.partner1.id,
                'lines': [(0, 0, {
                    'name': "OL/0001",
                    'product_id': tracked_product.id,
                    'price_unit': 1.15,
                    'discount': 0.0,
                    'qty': 1.0,
                    'tax_ids': [(6, 0, tracked_product.taxes_id.ids)],
                    'price_subtotal': untax,
                    'price_subtotal_incl': untax + atax,
                    'pack_lot_ids': [[0, 0, {'lot_name': lot.name}]],
                }), (0, 0, {
                    'name': "OL/0002",
                    'product_id': untracked_product.id,
                    'price_unit': 1.15,
                    'discount': 0.0,
                    'qty': 1.0,
                    'tax_ids': [(6, 0, untracked_product.taxes_id.ids)],
                    'price_subtotal': untax,
                    'price_subtotal_incl': untax + atax,
                })],
                'amount_tax': 2 * atax,
                'amount_total': 2 * (untax + atax),
                'amount_paid': 0,
                'amount_return': 0,
            })

            context_make_payment = {
                "active_ids": [pos_order.id],
                "active_id": pos_order.id,
            }
            pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
                'amount': 2 * (untax + atax),
            })
            context_payment = {'active_id': pos_order.id}
            pos_make_payment.with_context(context_payment).check()

            self.assertEqual(pos_order.state, 'paid')
            tracked_line = pos_order.picking_ids.move_line_ids.filtered(lambda ml: ml.product_id.id == tracked_product.id)
            untracked_line = pos_order.picking_ids.move_line_ids - tracked_line
            self.assertEqual(tracked_line.lot_id, lot)
            self.assertFalse(untracked_line.lot_id)
            self.assertEqual(tracked_line.location_id, shelf1_location)
            self.assertEqual(untracked_line.location_id, shelf1_location)

        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_order_to_invoice(self):

        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        untax1, atax1 = self.compute_tax(self.product3, 450*0.95, 2)
        untax2, atax2 = self.compute_tax(self.product4, 300*0.95, 3)
        # I create a new PoS order with 2 units of PC1 at 450 EUR (Tax Incl) and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 5.0,
                'qty': 2.0,
                'tax_ids': [(6, 0, self.product3.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id).ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 5.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.filtered(lambda t: t.company_id.id == self.env.company.id).ids)],
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
        if invoice.state != 'posted':
            invoice.action_post()
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
            'company_id': self.env.company.id,
        })
        # I create a bank statement with Opening and Closing balance 0.
        account_statement = self.AccountBankStatement.create({
            'balance_start': 0.0,
            'balance_end_real': 0.0,
            'date': time.strftime('%Y-%m-%d'),
            'journal_id': journal.id,
            'company_id': self.env.company.id,
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

        # I click on create a new session button
        self.pos_config.open_ui()

        current_session = self.pos_config.current_session_id
        num_starting_orders = len(current_session.order_ids)

        current_session.set_cashbox_pos(0, None)

        untax, atax = self.compute_tax(self.led_lamp, 0.9)
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

        untax, atax = self.compute_tax(self.whiteboard_pen, 1.2)
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
           'partner_id': self.partner1.id,
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

        untax, atax = self.compute_tax(self.newspaper_rack, 1.28)
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
        total_cash_payment = sum(current_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        current_session.post_closing_cash_details(total_cash_payment)
        current_session.close_session_from_ui()
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
        total_cash_payment = sum(rescue_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        rescue_session.post_closing_cash_details(total_cash_payment)
        rescue_session.close_session_from_ui()
        self.assertEqual(rescue_session.state, 'closed', "Rescue session was not properly closed")

    def test_order_to_payment_currency(self):
        """
            In order to test the Point of Sale in module, I will do a full flow from the sale to the payment and invoicing.
            I will use two products, one with price including a 10% tax, the other one with 5% tax excluded from the price.
            The order will be in a different currency than the company currency.
        """
        # Make sure the company is in USD
        self.env.ref('base.USD').active = True
        self.env.ref('base.EUR').active = True
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
            'journal_id': sale_journal.id,
            'use_pricelist': True,
            'available_pricelist_ids': [(6, 0, eur_pricelist.ids)],
            'pricelist_id': eur_pricelist.id,
            'payment_method_ids': [(6, 0, self.bank_payment_method.ids)]
        })

        # I click on create a new session button
        eur_config.open_ui()
        current_session = eur_config.current_session_id

        # I create a PoS order with 2 units of PCSC234 at 450 EUR (Tax Incl)
        # and 3 units of PCSC349 at 300 EUR. (Tax Excl)

        untax1, atax1 = self.compute_tax(self.product3, 450, 2)
        untax2, atax2 = self.compute_tax(self.product4, 300, 3)
        self.pos_order_pos0 = self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'pricelist_id': eur_pricelist.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product3.id,
                'price_unit': 450,
                'discount': 0.0,
                'qty': 2.0,
                'tax_ids': [(6, 0, self.product3.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
                'price_subtotal': untax1,
                'price_subtotal_incl': untax1 + atax1,
            }), (0, 0, {
                'name': "OL/0002",
                'product_id': self.product4.id,
                'price_unit': 300,
                'discount': 0.0,
                'qty': 3.0,
                'tax_ids': [(6, 0, self.product4.taxes_id.filtered(lambda t: t.company_id == self.env.company).ids)],
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
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # I create a new PoS order with 2 units of PC1 at 450 EUR (Tax Incl) and 3 units of PCSC349 at 300 EUR. (Tax Excl)
        self.pos_order_pos1 = self.PosOrder.create({
            'company_id': self.env.company.id,
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
        if invoice.state != 'posted':
            invoice.action_post()
        self.assertAlmostEqual(
            invoice.amount_total, self.pos_order_pos1.amount_total, places=2, msg="Invoice not correct")

        for iline in invoice.invoice_line_ids:
            self.assertFalse(iline.tax_ids)

        self.pos_config.current_session_id.action_pos_session_closing_control()

    def test_order_with_deleted_tax(self):
        # create tax
        dummy_50_perc_tax = self.env['account.tax'].create({
            'name': 'Tax 50%',
            'amount_type': 'percent',
            'amount': 50.0,
            'price_include': 0
        })

        # set tax to product
        product5 = self.env['product.product'].create({
            'name': 'product5',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
            'taxes_id': dummy_50_perc_tax.ids
        })

        # sell product thru pos
        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        untax, atax = self.compute_tax(product5, 10.0)
        product5_order = {'data':
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
              'price_unit': 10.0,
              'product_id': product5.id,
              'price_subtotal': 10.0,
              'price_subtotal_incl': 15.0,
              'qty': 1,
              'tax_ids': [(6, 0, product5.taxes_id.ids)]}]],
           'name': 'Order 12345-123-1234',
           'partner_id': False,
           'pos_session_id': pos_session.id,
           'sequence_number': 2,
           'statement_ids': [[0,
             0,
             {'amount': untax + atax,
              'name': fields.Datetime.now(),
              'payment_method_id': self.cash_payment_method.id}]],
           'uid': '12345-123-1234',
           'user_id': self.env.uid},
          'id': '12345-123-1234',
          'to_invoice': False}
        self.PosOrder.create_from_ui([product5_order])

        # delete tax
        dummy_50_perc_tax.unlink()

        total_cash_payment = sum(pos_session.mapped('order_ids.payment_ids').filtered(lambda payment: payment.payment_method_id.type == 'cash').mapped('amount'))
        pos_session.post_closing_cash_details(total_cash_payment)

        # close session (should not fail here)
        # We don't call `action_pos_session_closing_control` to force the failed
        # closing which will return the action because the internal rollback call messes
        # with the rollback of the test runner. So instead, we directly call the method
        # that returns the action by specifying the imbalance amount.
        action = pos_session._close_session_action(5.0)
        wizard = self.env['pos.close.session.wizard'].browse(action['res_id'])
        wizard.with_context(action['context']).close_session()

        # check the difference line
        diff_line = pos_session.move_id.line_ids.filtered(lambda line: line.name == 'Difference at closing PoS session')
        self.assertAlmostEqual(diff_line.credit, 5.0, msg="Missing amount of 5.0")

    def test_order_multi_step_route(self):
        """ Test that orders in sessions with "Ship Later" enabled and "Specific Route" set to a
            multi-step (2/3) route can be validated. This config implies multiple picking types
            and multiple move_lines.
        """
        tracked_product = self.env['product.product'].create({
            'name': 'SuperProduct Tracked',
            'type': 'product',
            'tracking': 'lot',
            'available_in_pos': True
        })
        tracked_product_2 = self.env['product.product'].create({
            'name': 'SuperProduct Tracked 2',
            'type': 'product',
            'tracking': 'lot',
            'available_in_pos': True
        })
        tracked_product_2_lot = self.env['stock.lot'].create({
            'name': '80085',
            'product_id': tracked_product_2.id,
            'company_id': self.env.company.id,
        })
        stock_location = self.company_data['default_warehouse'].lot_stock_id
        self.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': tracked_product_2.id,
            'inventory_quantity': 1,
            'location_id': stock_location.id,
            'lot_id': tracked_product_2_lot.id
        }).action_apply_inventory()
        warehouse_id = self.company_data['default_warehouse']
        warehouse_id.delivery_steps = 'pick_ship'

        self.pos_config.ship_later = True
        self.pos_config.warehouse_id = warehouse_id
        self.pos_config.route_id = warehouse_id.route_ids[-1]
        self.pos_config.open_ui()
        self.pos_config.current_session_id.update_stock_at_closing = False

        untax, tax = self.compute_tax(tracked_product, 1.15, 1)

        pos_order = self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': self.pos_config.current_session_id.id,
            'pricelist_id': self.partner1.property_product_pricelist.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': tracked_product.id,
                'price_unit': 1.15,
                'qty': 1.0,
                'price_subtotal': untax,
                'price_subtotal_incl': untax + tax,
                'pack_lot_ids': [
                    [0, 0, {'lot_name': '80085'}],
                ]
            }),
                (0, 0, {
                    'name': "OL/0002",
                    'product_id': tracked_product_2.id,
                    'price_unit': 1.15,
                    'qty': 1.0,
                    'price_subtotal': untax,
                    'price_subtotal_incl': untax + tax,
                    'pack_lot_ids': [
                        [0, 0, {'lot_name': '80085'}],
                    ]
            })],
            'amount_tax': tax,
            'amount_total': untax+tax,
            'amount_paid': 0,
            'amount_return': 0,
            'to_ship': True,
        })

        context_make_payment = {
            "active_ids": [pos_order.id],
            "active_id": pos_order.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': untax+tax,
        })
        context_payment = {'active_id': pos_order.id}
        pos_make_payment.with_context(context_payment).check()
        pickings = pos_order.picking_ids
        picking_mls_no_stock = pickings.move_line_ids.filtered(lambda l: l.product_id.id == tracked_product.id)
        picking_mls_stock = pickings.move_line_ids.filtered(lambda l: l.product_id.id == tracked_product_2.id)
        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(len(picking_mls_no_stock), 0)
        self.assertEqual(len(picking_mls_stock), 1)
        self.assertEqual(len(pickings.picking_type_id), 2)

    def test_order_refund_picking(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id
        current_session.update_stock_at_closing = True
        # I create a new PoS order with 1 line
        order = self.PosOrder.create({
            'company_id': self.env.company.id,
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
            })],
            'amount_total': 1710.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'to_invoice': True
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

        payment_context = {"active_ids": refund.ids, "active_id": refund.id}
        refund_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': refund.amount_total,
            'payment_method_id': self.cash_payment_method.id,
        })

        # I click on the validate button to register the payment.
        refund_payment.with_context(**payment_context).check()

        refund.action_pos_order_invoice()
        self.assertEqual(refund.picking_count, 1)

    def test_order_with_different_payments_and_refund(self):
        """
        Test that all the payments are correctly taken into account when the order contains multiple payments and money refund.
        In this example, we create an order with two payments for a product of 750$:
            - one payment of $300 with customer account
            - one payment of $460 with cash
        Then, we refund the order with $10, and check that the amount still due is 300$.
        """

        product5 = self.env['product.product'].create({
            'name': 'product5',
            'type': 'product',
            'categ_id': self.env.ref('product.product_category_all').id,
        })

        # sell product thru pos
        self.pos_config.open_ui()
        pos_session = self.pos_config.current_session_id
        product5_order = {'data':
          {'amount_paid': 750,
           'amount_return': 10,
           'amount_tax': 0,
           'amount_total': 750,
           'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
           'fiscal_position_id': False,
           'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
           'lines': [[0, 0, {
                'discount': 0,
                'id': 42,
                'pack_lot_ids': [],
                'price_unit': 750.0,
                'product_id': product5.id,
                'price_subtotal': 750.0,
                'price_subtotal_incl': 750.0,
                'tax_ids': [[6, False, []]],
                'qty': 1,
            }]],
           'name': 'Order 12345-123-1234',
           'partner_id': self.partner1.id,
           'pos_session_id': pos_session.id,
           'sequence_number': 2,
           'statement_ids': [[0, 0, {
                'amount': 460,
                'name': fields.Datetime.now(),
                'payment_method_id': self.cash_payment_method.id
            }], [0, 0, {
                'amount': 300,
                'name': fields.Datetime.now(),
                'payment_method_id': self.credit_payment_method.id
            }]],
           'uid': '12345-123-1234',
           'user_id': self.env.uid,
           'to_invoice': True, }
        }
        pos_order_id = self.PosOrder.create_from_ui([product5_order])[0]['id']
        pos_order = self.PosOrder.search([('id', '=', pos_order_id)])
        #assert account_move amount_residual is 300
        self.assertEqual(pos_order.account_move.amount_residual, 300)

    def test_sale_order_postponed_invoicing(self):
        """ Test the flow of creating an invoice later, after the POS session has been closed and everything has been processed.
        The process should:
           - Create a new misc entry, that will revert part of the POS closing entry.
           - Create the move and associating payment(s) entry, as it would do when closing with invoice.
           - Reconcile the receivable lines from the created misc entry with the ones from the created payment(s)
        """
        # Create the order on the first of january.
        with freeze_time('2020-01-01'):
            product = self.env['product.product'].create({
                'name': 'Dummy product',
                'type': 'product',
                'categ_id': self.env.ref('product.product_category_all').id,
                'taxes_id': self.tax_sale_a.ids,
            })
            self.pos_config.open_ui()
            pos_session = self.pos_config.current_session_id
            untax, atax = self.compute_tax(product, 500, 1)
            pos_order_data = {
                'data': {
                    'amount_paid': untax + atax,
                    'amount_return': 0,
                    'amount_tax': atax,
                    'amount_total': untax + atax,
                    'creation_date': fields.Datetime.to_string(fields.Datetime.now()),
                    'fiscal_position_id': False,
                    'pricelist_id': self.pos_config.available_pricelist_ids[0].id,
                    'lines': [(0, 0, {
                        'discount': 0,
                        'id': 42,
                        'pack_lot_ids': [],
                        'price_unit': 500.0,
                        'product_id': product.id,
                        'price_subtotal': 500.0,
                        'price_subtotal_incl': 575.0,
                        'qty': 1,
                        'tax_ids': [(6, 0, product.taxes_id.ids)]
                    })],
                    'name': 'Order 12345-123-1234',
                    'partner_id': False,
                    'pos_session_id': pos_session.id,
                    'sequence_number': 2,
                    'statement_ids': [(0, 0, {
                        'amount': untax + atax,
                        'name': fields.Datetime.now(),
                        'payment_method_id': self.cash_payment_method.id
                    })],
                    'uid': '12345-123-1234',
                    'user_id': self.env.uid
                },
                'id': '12345-123-1234',
                'to_invoice': False
            }
            pos_order_id = self.PosOrder.create_from_ui([pos_order_data])[0]['id']
            pos_order = self.env['pos.order'].browse(pos_order_id)
            # End the session. The order has been created without any invoice.
            self.pos_config.current_session_id.action_pos_session_closing_control()
            self.assertFalse(pos_order.account_move.exists())
        # Client is back on the 3rd, asks for an invoice.
        with freeze_time('2020-01-03'):
            # We set the partner on the order
            pos_order.partner_id = self.partner1.id
            pos_order.action_pos_order_invoice()
            # We should now have: an invoice, a payment, and a misc entry reconciled with the payment that reverse the original POS closing entry.
            invoice = pos_order.account_move
            closing_entry = pos_order.session_move_id
            # This search isn't the best, but we don't have any references to this move stored on other models.
            misc_reversal_entry = self.env['account.move'].search([('ref', '=', f'Reversal of POS closing entry {closing_entry.name} for order {pos_order.name} from session {pos_order.session_id.name}')])
            # In this case we will have only one, for cash payment
            payment = self.env['account.move'].search([('ref', '=like', f'Invoice payment for {pos_order.name} ({pos_order.account_move.name}) using {self.cash_payment_method.name}')])
            # And thus only one bank statement for it
            statement = self.env['account.move'].search([('journal_id', '=', self.company_data['default_journal_cash'].id)])
            self.assertTrue(invoice.exists() and closing_entry.exists() and misc_reversal_entry.exists() and payment.exists())
            # Check 1: Check that we have reversed every credit line on the closing entry.
            for closing_entry_line, misc_reversal_entry_line in zip(closing_entry.line_ids, misc_reversal_entry.line_ids):
                if closing_entry_line.balance < 0:
                    self.assertEqual(closing_entry_line.balance, -misc_reversal_entry_line.balance)
                    self.assertEqual(closing_entry_line.account_id, misc_reversal_entry_line.account_id)

            # Check 2: Reconciliation
            # The invoice receivable should be reconciled with the payment receivable of the same account.
            invoice_receivable_line = invoice.line_ids.filtered(lambda line: line.account_id == self.company_data['default_account_receivable'])
            payment_receivable_line = payment.line_ids.filtered(lambda line: line.account_id == self.company_data['default_account_receivable'])
            self.assertEqual(invoice_receivable_line.matching_number, payment_receivable_line.matching_number)
            # The payment receivable (POS) is reconciled with the closing entry receivable (POS)
            payment_receivable_pos_line = payment.line_ids.filtered(lambda line: line.account_id == self.company_data['company'].account_default_pos_receivable_account_id)
            misc_receivable_pos_line = misc_reversal_entry.line_ids.filtered(lambda line: line.account_id == self.company_data['company'].account_default_pos_receivable_account_id)
            self.assertEqual(misc_receivable_pos_line.matching_number, payment_receivable_pos_line.matching_number)
            # The closing entry receivable is reconciled with the bank statement
            closing_entry_receivable_line = closing_entry.line_ids.filtered(lambda line: line.account_id == self.company_data['default_account_receivable'])  # Because the payment method use the default receivable
            statement_receivable_line = statement.line_ids.filtered(lambda line: line.account_id == self.company_data['default_account_receivable'] and line.name == pos_order.session_id.name)  # Because the payment method use the default receivable
            self.assertEqual(closing_entry_receivable_line.matching_number, statement_receivable_line.matching_number)
