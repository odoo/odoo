# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from unittest.mock import patch

from odoo import fields
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestStockValuation(TransactionCase):
    def setUp(self):
        super(TestStockValuation, self).setUp()
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product1 = self.env.ref('product.product_product_8')
        Account = self.env['account.account']
        self.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        self.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        self.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'Stock Valuation',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_journal = self.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        self.product1.categ_id.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })

    def test_change_unit_cost_average_1(self):
        """ Confirm a purchase order and create the associated receipt, change the unit cost of the
        purchase order before validating the receipt, the value of the received goods should be set
        according to the last unit cost.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_lines[0]

        # the unit price of the purchase order line is copied to the in move
        self.assertEquals(move1.price_unit, 100)

        # update the unit price on the purchase order line
        po1.order_line.price_unit = 200

        # the unit price on the stock move is not directly updated
        self.assertEquals(move1.price_unit, 100)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # the unit price of the valuationlayer used the latest value
        self.assertEquals(move1.stock_valuation_layer_ids.unit_cost, 200)

        self.assertEquals(self.product1.value_svl, 2000)

    def test_standard_price_change_1(self):
        """ Confirm a purchase order and create the associated receipt, change the unit cost of the
        purchase order and the standard price of the product before validating the receipt, the
        value of the received goods should be set according to the last standard price.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'

        # set a standard price
        self.product1.product_tmpl_id.standard_price = 10

        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 11.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_lines[0]

        # the move's unit price reflects the purchase order line's cost even if it's useless when
        # the product's cost method is standard
        self.assertEquals(move1.price_unit, 11)

        # set a new standard price
        self.product1.product_tmpl_id.standard_price = 12

        # the unit price on the stock move is not directly updated
        self.assertEquals(move1.price_unit, 11)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # the unit price of the valuation layer used the latest value
        self.assertEquals(move1.stock_valuation_layer_ids.unit_cost, 12)

        self.assertEquals(self.product1.value_svl, 120)

    def test_change_currency_rate_average_1(self):
        """ Confirm a purchase order in another currency and create the associated receipt, change
        the currency rate, validate the receipt and then check that the value of the received goods
        is set according to the last currency rate.
        """
        self.env['res.currency.rate'].search([]).unlink()
        usd_currency = self.env.ref('base.USD')
        self.env.company.currency_id = usd_currency.id

        eur_currency = self.env.ref('base.EUR')

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        # default currency is USD, create a purchase order in EUR
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'currency_id': eur_currency.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_lines[0]

        # convert the price unit in the company currency
        price_unit_usd = po1.currency_id._convert(
            po1.order_line.price_unit, po1.company_id.currency_id,
            self.env.company, fields.Date.today(), round=False)

        # the unit price of the move is the unit price of the purchase order line converted in
        # the company's currency
        self.assertAlmostEqual(move1.price_unit, price_unit_usd, places=2)

        # change the rate of the currency
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y-%m-%d'),
            'rate': 2.0,
            'currency_id': eur_currency.id,
            'company_id': po1.company_id.id,
        })
        eur_currency._compute_current_rate()
        price_unit_usd_new_rate = po1.currency_id._convert(
            po1.order_line.price_unit, po1.company_id.currency_id,
            self.env.company, fields.Date.today(), round=False)

        # the new price_unit is lower than th initial because of the rate's change
        self.assertLess(price_unit_usd_new_rate, price_unit_usd)

        # the unit price on the stock move is not directly updated
        self.assertAlmostEqual(move1.price_unit, price_unit_usd, places=2)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # the unit price of the valuation layer used the latest value
        self.assertAlmostEqual(move1.stock_valuation_layer_ids.unit_cost, price_unit_usd_new_rate)

        self.assertAlmostEqual(self.product1.value_svl, price_unit_usd_new_rate * 10, delta=0.1)

    def test_extra_move_fifo_1(self):
        """ Check that the extra move when over processing a receipt is correctly merged back in
        the original move.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_lines[0]
        move1.quantity_done = 15
        res_dict = picking1.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.overprocessed.transfer')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.action_confirm()

        # there should be only one move
        self.assertEqual(len(picking1.move_lines), 1)
        self.assertEqual(move1.price_unit, 100)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 100)
        self.assertEqual(move1.product_qty, 15)
        self.assertEqual(self.product1.value_svl, 1500)

    def test_backorder_fifo_1(self):
        """ Check that the backordered move when under processing a receipt correctly keep the
        price unit of the original move.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_lines[0]
        move1.quantity_done = 5
        res_dict = picking1.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        self.assertEqual(len(picking1.move_lines), 1)
        self.assertEqual(move1.price_unit, 100)
        self.assertEqual(move1.product_qty, 5)

        picking2 = po1.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_lines[0]
        self.assertEqual(len(picking2.move_lines), 1)
        self.assertEqual(move2.price_unit, 100)
        self.assertEqual(move2.product_qty, 5)


@tagged('post_install', '-at_install')
class TestStockValuationWithCOA(AccountingTestCase):
    def setUp(self):
        super(TestStockValuationWithCOA, self).setUp()
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product1 = self.env.ref('product.product_product_8')

        cat = self.env['product.category'].create({
            'name': 'cat',
        })
        self.product1 = self.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
            'categ_id': cat.id,
        })

        Account = self.env['account.account']
        self.usd_currency = self.env.ref('base.USD')
        self.eur_currency = self.env.ref('base.EUR')

        self.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        self.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
            'reconcile': True,
        })
        self.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'Stock Valuation',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.price_diff_account = Account.create({
            'name': 'price diff account',
            'code': 'price diff account',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_journal = self.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        self.product1.categ_id.write({
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })

    def test_fifo_anglosaxon_return(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'
        self.product1.property_account_creditor_price_difference = self.price_diff_account

        # Receive 10@10 ; create the vendor bill
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 10.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()
        receipt_po1 = po1.picking_ids[0]
        receipt_po1.move_lines.quantity_done = 10
        receipt_po1.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        move_form.partner_id = self.partner_id
        move_form.purchase_id = po1
        invoice_po1 = move_form.save()
        invoice_po1.post()

        # Receive 10@20 ; create the vendor bill
        po2 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 20.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po2.button_confirm()
        receipt_po2 = po2.picking_ids[0]
        receipt_po2.move_lines.quantity_done = 10
        receipt_po2.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        move_form.partner_id = self.partner_id
        move_form.purchase_id = po2
        invoice_po2 = move_form.save()
        invoice_po2.post()

        # valuation of product1 should be 300
        self.assertEqual(self.product1.value_svl, 300)

        # return the second po
        stock_return_picking_form = Form(self.env['stock.return.picking']
            .with_context(active_ids=receipt_po2.ids, active_id=receipt_po2.ids[0],
            active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 10
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 10
        return_pick.button_validate()

        # valuation of product1 should be 200 as the first items will be sent out
        self.assertEqual(self.product1.value_svl, 200)

        # create a credit note for po2
        move_form = Form(self.env['account.move'].with_context(default_type='in_refund'))
        move_form.partner_id = self.partner_id
        move_form.purchase_id = po2
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 10
        creditnote_po2 = move_form.save()
        creditnote_po2.post()

        # check the anglo saxon entries
        price_diff_entry = self.env['account.move.line'].search([('account_id', '=', self.price_diff_account.id)])
        self.assertEqual(price_diff_entry.credit, 100)

    def test_anglosaxon_valuation(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'
        self.product1.property_account_creditor_price_difference = self.price_diff_account

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_lines.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price
        move_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        move_form.partner_id = order.partner_id
        move_form.purchase_id = order
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 15.0
        invoice = move_form.save()
        invoice.post()

        # Check what was posted in the price difference account
        price_diff_aml = self.env['account.move.line'].search([('account_id','=', self.price_diff_account.id)])
        self.assertEquals(len(price_diff_aml), 1, "Only one line should have been generated in the price difference account.")
        self.assertAlmostEquals(price_diff_aml.debit, 5, "Price difference should be equal to 5 (15-10)")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id','=',self.stock_input_account.id)])
        self.assertEquals(len(input_aml), 3, "Only three lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        invoice_amls = input_aml.filtered(lambda l: l.move_id == invoice)
        picking_aml = input_aml - invoice_amls
        self.assertAlmostEquals(sum(invoice_amls.mapped('debit')), 15, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEquals(sum(invoice_amls.mapped('credit')), 5, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEquals(sum(picking_aml.mapped('credit')), 10, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_valuation_from_increasing_tax(self):
        """ Check that a tax without account will increment the stock value.
        """

        tax_with_no_account = self.env['account.tax'].create({
            'name': "Tax with no account",
            'amount_type': 'fixed',
            'amount': 5,
            'sequence': 8,
        })

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.valuation = 'real_time'


        # Receive 10@10 ; create the vendor bill
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'taxes_id': [(4, tax_with_no_account.id)],
                    'product_qty': 10.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 10.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()
        receipt_po1 = po1.picking_ids[0]
        receipt_po1.move_lines.quantity_done = 10
        receipt_po1.button_validate()

        # valuation of product1 should be 15 as the tax with no account set
        # has gone to the stock account, and must be reflected in inventory valuation
        self.assertEqual(self.product1.value_svl, 150)

    def test_average_realtime_anglo_saxon_valuation_multicurrency_same_date(self):
        """
        The PO and invoice are in the same foreign currency.
        The PO is invoiced on the same date as its creation.
        This shouldn't create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True

        date_po = '2019-01-01'

        # SetUp product
        self.product1.product_tmpl_id.cost_method = 'average'
        self.product1.product_tmpl_id.valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'order'
        self.product1.product_tmpl_id.purchase_method = 'purchase'

        self.product1.property_account_creditor_price_difference = self.price_diff_account

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        inv = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'invoice_date': date_po,
            'date': date_po,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'price_unit': 100.0,
                'product_id': self.product1.id,
                'purchase_line_id': po.order_line.id,
                'quantity': 1.0,
                'account_id': self.stock_input_account.id,
            })]
        })

        inv.post()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 2)

        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(payable_line.amount_currency, -100.0)
        self.assertAlmostEqual(payable_line.balance, -66.67)

        stock_line = move_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertEqual(stock_line.amount_currency, 100.0)
        self.assertAlmostEqual(stock_line.balance, 66.67)

    def test_realtime_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The PO is invoiced at a later date than its creation.
        This should create a price difference entry for standard cost method
        Not for average cost method though, since the PO and invoice have the same currency
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date_po = '2019-01-01'
        date_invoice = '2019-01-16'

        # SetUp product Average
        self.product1.product_tmpl_id.write({
            'purchase_method': 'purchase',
            'property_account_creditor_price_difference': self.price_diff_account.id,
        })
        self.product1.invoice_policy = 'order'

        # SetUp product Standard
        # should have bought at 60 USD
        # actually invoiced at 70 EUR > 35 USD
        product_categ_standard = self.product1.product_tmpl_id.categ_id.copy({
            'property_cost_method': 'standard',
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })
        product_standard = self.product1.copy({
            'categ_id': product_categ_standard.id,
            'name': 'Standard Val',
            'standard_price': 60,
            'property_account_creditor_price_difference': self.price_diff_account.id
        })

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # To allow testing validation of PO
        def _today(*args, **kwargs):
            return date_po
        patchers = [
            patch('odoo.fields.Date.context_today', _today),
        ]

        for p in patchers:
            p.start()

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': date_po,
                }),
                (0, 0, {
                    'name': product_standard.name,
                    'product_id': product_standard.id,
                    'product_qty': 1.0,
                    'product_uom': product_standard.uom_po_id.id,
                    'price_unit': 40.0,
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        line_product_average = po.order_line.filtered(lambda l: l.product_id == self.product1)
        line_product_standard = po.order_line.filtered(lambda l: l.product_id == product_standard)

        inv = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': self.product1.name,
                    'price_subtotal': 100.0,
                    'price_unit': 100.0,
                    'product_id': self.product1.id,
                    'purchase_line_id': line_product_average.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                }),
                (0, 0, {
                    'name': product_standard.name,
                    'price_subtotal': 70.0,
                    'price_unit': 70.0,
                    'product_id': product_standard.id,
                    'purchase_line_id': line_product_standard.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv.post()

        for p in patchers:
            p.stop()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 5)

        # Ensure no exchange difference move has been created
        self.assertTrue(all([not l.reconciled for l in move_lines]))

        # PAYABLE CHECK
        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(payable_line.amount_currency, -170.0)
        self.assertAlmostEqual(payable_line.balance, -85.00)

        # PRODUCTS CHECKS

        # NO EXCHANGE DIFFERENCE (average)
        # We ordered for a value of 100 EUR
        # But by the time we are invoiced for it
        # the foreign currency appreciated from 1.5 to 2.0
        # We still have to pay 100 EUR, which now values at 50 USD
        product_lines = move_lines.filtered(lambda l: l.product_id == self.product1)

        # Stock-wise, we have been invoiced 100 EUR, and we ordered 100 EUR
        # there is no price difference
        # However, 100 EUR should be converted at the time of the invoice
        stock_lines = product_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 100.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 50.00)

        # PRICE DIFFERENCE (STANDARD)
        # We ordered a product that should have cost 60 USD (120 EUR)
        # However, we effectively got invoiced 70 EUR (35 USD)
        product_lines = move_lines.filtered(lambda l: l.product_id == product_standard)

        stock_lines = product_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 120.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 60.00)

        price_diff_line = product_lines.filtered(lambda l: l.account_id == self.price_diff_account)
        self.assertEqual(price_diff_line.amount_currency, -50.00)
        self.assertAlmostEqual(price_diff_line.balance, -25.00)

    def test_average_realtime_with_delivery_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The delivery occurs in between PO validation and invoicing
        The invoice is created at an even different date
        This should create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date_po = '2019-01-01'
        date_delivery = '2019-01-08'
        date_invoice = '2019-01-16'

        product_avg = self.product1.copy({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 60,
            'property_account_creditor_price_difference': self.price_diff_account.id
        })
        product_avg.invoice_policy = 'order'

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_delivery,
            'rate': 0.7,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # To allow testing validation of PO
        def _today(*args, **kwargs):
            return datetime.strptime(date_po, "%Y-%m-%d").date()
        # To allow testing validation of Delivery
        def _now(*args, **kwargs):
            return datetime.strptime(date_delivery + ' 01:00:00', "%Y-%m-%d %H:%M:%S")

        patchers = [
            patch('odoo.fields.Date.context_today', _today),
            patch('odoo.fields.Datetime.now', _now),
        ]

        for p in patchers:
            p.start()

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_avg.name,
                    'product_id': product_avg.id,
                    'product_qty': 1.0,
                    'product_uom': product_avg.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': date_po,
                })
            ],
        })
        po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)

        picking = po.picking_ids
        (picking.move_lines
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity_done': 1.0}))

        picking.button_validate()

        inv = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': product_avg.name,
                    'price_unit': 30.0,
                    'product_id': product_avg.id,
                    'purchase_line_id': line_product_avg.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv.post()

        for p in patchers:
            p.stop()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 2)

        # PAYABLE CHECK
        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(payable_line.amount_currency, -30.0)
        self.assertAlmostEqual(payable_line.balance, -15.00)

        # PRODUCTS CHECKS

        # DELIVERY DIFFERENCE (AVERAGE)
        # We ordered a product at 30 EUR valued at 20 USD
        # We received it when the exchange rate has appreciated
        # So, the actualized 20 USD are now 20*1.5/0.7 = 42.86 USD
        product_lines = move_lines.filtered(lambda l: l.product_id == product_avg)

        # Although those 42.86 USD are just due to the exchange difference
        stock_line = product_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertEqual(stock_line.journal_id, inv.journal_id)
        self.assertEqual(stock_line.amount_currency, 30.00)
        self.assertAlmostEqual(stock_line.balance, 15.00)
        full_reconcile = stock_line.full_reconcile_id
        self.assertTrue(full_reconcile.exists())

        reconciled_lines = full_reconcile.reconciled_line_ids - stock_line
        self.assertEqual(len(reconciled_lines), 2)

        stock_journal_line = reconciled_lines.filtered(lambda l: l.journal_id == self.stock_journal)
        self.assertEqual(stock_journal_line.amount_currency, -30.00)
        self.assertAlmostEqual(stock_journal_line.balance, -42.86)

        exhange_diff_journal = company.currency_exchange_journal_id.exists()
        exchange_stock_line = reconciled_lines.filtered(lambda l: l.journal_id == exhange_diff_journal)
        self.assertEqual(exchange_stock_line.amount_currency, 0.00)
        self.assertAlmostEqual(exchange_stock_line.balance, 27.86)

    def test_average_realtime_with_two_delivery_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The deliveries occur at different times and rates
        The invoice is created at an even different date
        This should create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        exchange_diff_journal = company.currency_exchange_journal_id.exists()

        date_po = '2019-01-01'
        date_delivery = '2019-01-08'
        date_delivery1 = '2019-01-10'
        date_invoice = '2019-01-16'
        date_invoice1 = '2019-01-20'

        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.categ_id.property_cost_method = 'average'
        product_avg = self.product1.copy({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 60,
            'property_account_creditor_price_difference': self.price_diff_account.id
        })
        product_avg.invoice_policy = 'order'

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_delivery,
            'rate': 0.7,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_delivery1,
            'rate': 0.8,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        self.env['res.currency.rate'].create({
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_invoice1,
            'rate': 2.2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # To allow testing validation of PO
        def _today(*args, **kwargs):
            return datetime.strptime(date_po, "%Y-%m-%d").date()
        # To allow testing validation of Delivery
        delivery_now = date_delivery
        def _now(*args, **kwargs):
            return datetime.strptime(delivery_now + ' 01:00:00', "%Y-%m-%d %H:%M:%S")

        patchers = [
            patch('odoo.fields.Date.context_today', _today),
            patch('odoo.fields.Datetime.now', _now),
        ]

        for p in patchers:
            p.start()

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'date_order': date_po,
            'order_line': [
                (0, 0, {
                    'name': product_avg.name,
                    'product_id': product_avg.id,
                    'product_qty': 10.0,
                    'product_uom': product_avg.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': date_po,
                })
            ],
        })
        po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)

        picking = po.picking_ids
        (picking.move_lines
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity_done': 5.0}))

        picking.button_validate()
        picking.action_done()  # Create Backorder

        inv = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'invoice_date': date_invoice,
            'date': date_invoice,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': product_avg.name,
                    'price_unit': 20.0,
                    'product_id': product_avg.id,
                    'purchase_line_id': line_product_avg.id,
                    'quantity': 5.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv.post()

        backorder_picking = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
        delivery_now = date_delivery1
        (backorder_picking.move_lines
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity_done': 5.0}))
        backorder_picking.button_validate()

        inv1 = self.env['account.move'].with_context(default_type='in_invoice').create({
            'type': 'in_invoice',
            'invoice_date': date_invoice1,
            'date': date_invoice1,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {
                    'name': product_avg.name,
                    'price_unit': 40.0,
                    'product_id': product_avg.id,
                    'purchase_line_id': line_product_avg.id,
                    'quantity': 5.0,
                    'account_id': self.stock_input_account.id,
                })
            ]
        })

        inv1.post()

        for p in patchers:
            p.stop()

        ##########################
        #       Invoice 0        #
        ##########################
        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 4)

        # PAYABLE CHECK
        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(payable_line.amount_currency, -100.0)
        self.assertAlmostEqual(payable_line.balance, -50.00)

        # # PRODUCTS CHECKS

        # DELIVERY DIFFERENCE (AVERAGE)
        stock_lines = move_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertEqual(len(stock_lines), 2)
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 150.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 75.00)

        price_diff_line = move_lines.filtered(lambda l: l.account_id == self.price_diff_account)
        self.assertAlmostEqual(price_diff_line.amount_currency, -50.00)
        self.assertAlmostEqual(price_diff_line.balance, -25.00)

        full_reconcile = stock_lines.mapped('full_reconcile_id')
        self.assertTrue(full_reconcile.exists())

        reconciled_lines = full_reconcile.reconciled_line_ids - stock_lines
        self.assertEqual(len(reconciled_lines), 2)

        stock_journal_line = reconciled_lines.filtered(lambda l: l.journal_id == self.stock_journal)
        self.assertEqual(stock_journal_line.amount_currency, -150)
        self.assertAlmostEqual(stock_journal_line.balance, -214.29)

        exchange_stock_line = reconciled_lines.filtered(lambda l: l.journal_id == exchange_diff_journal)
        self.assertEqual(exchange_stock_line.amount_currency, 0.00)
        self.assertAlmostEqual(exchange_stock_line.balance, 139.29)

        ##########################
        #       Invoice 1        #
        ##########################
        move_lines = inv1.line_ids
        self.assertEqual(len(move_lines), 4)

        # PAYABLE CHECK
        payable_line = move_lines.filtered(lambda l: l.account_id.internal_type == 'payable')
        self.assertEqual(payable_line.amount_currency, -200.0)
        self.assertAlmostEqual(payable_line.balance, -90.91)

        # # PRODUCTS CHECKS

        # DELIVERY DIFFERENCE (AVERAGE)
        stock_lines = move_lines.filtered(lambda l: l.account_id == self.stock_input_account)
        self.assertEqual(stock_lines.mapped('journal_id'), inv.journal_id)
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 150.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 68.18)

        price_diff_line = move_lines.filtered(lambda l: l.account_id == self.price_diff_account)
        self.assertEqual(price_diff_line.amount_currency, 50.00)
        self.assertAlmostEqual(price_diff_line.balance, 22.73)

        full_reconcile = stock_lines.mapped('full_reconcile_id')
        self.assertTrue(full_reconcile.exists())

        reconciled_lines = full_reconcile.reconciled_line_ids - stock_lines
        self.assertEqual(len(reconciled_lines), 3)

        stock_journal_line = reconciled_lines.filtered(lambda l: l.journal_id == self.stock_journal)
        self.assertEqual(stock_journal_line.amount_currency, -150)
        self.assertAlmostEqual(stock_journal_line.balance, -187.5)

        exchange_stock_lines = reconciled_lines.filtered(lambda l: l.journal_id == exchange_diff_journal)
        self.assertAlmostEqual(sum(exchange_stock_lines.mapped('amount_currency')), 0.00)
        self.assertAlmostEqual(sum(exchange_stock_lines.mapped('balance')), 119.32)

    def test_anglosaxon_valuation_price_total_diff_discount(self):
        """
        PO:  price unit: 110
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'
        self.product1.property_account_creditor_price_difference = self.price_diff_account

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 110.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_lines.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.post()

        # Check what was posted in the price difference account
        price_diff_aml = self.env['account.move.line'].search([('account_id','=', self.price_diff_account.id)])
        self.assertEquals(len(price_diff_aml), 1, "Only one line should have been generated in the price difference account.")
        self.assertAlmostEquals(price_diff_aml.credit, 20, "Price difference should be equal to 20 (110-90)")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id','=', self.stock_input_account.id)])
        self.assertEquals(len(input_aml), 3, "Only two lines should have been generated in stock input account: one when receiving the product, two when making the invoice.")
        self.assertAlmostEquals(sum(input_aml.mapped('debit')), 110, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEquals(sum(input_aml.mapped('credit')), 110, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_discount(self):
        """
        PO:  price unit: 100
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'
        self.product1.property_account_creditor_price_difference = self.price_diff_account

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 100.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_lines.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.tax_ids.clear()
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.post()

        # Check what was posted in the price difference account
        price_diff_aml = self.env['account.move.line'].search([('account_id', '=', self.price_diff_account.id)])
        self.assertEquals(len(price_diff_aml), 1, "Only one line should have been generated in the price difference account.")
        self.assertAlmostEquals(price_diff_aml.credit, 10, "Price difference should be equal to 10 (100-90)")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEquals(len(input_aml), 3, "Three lines generated in stock input account: one when receiving the product, two when making the invoice.")
        self.assertAlmostEquals(sum(input_aml.mapped('debit')), 100, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEquals(sum(input_aml.mapped('credit')), 100, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_price_unit_diff_discount(self):
        """
        PO:  price unit:  90
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'
        self.product1.property_account_creditor_price_difference = self.price_diff_account

        # Create PO
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 90.0
        order = po_form.save()
        order.button_confirm()

        # Receive the goods
        receipt = order.picking_ids[0]
        receipt.move_lines.quantity_done = 1
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_type='in_invoice'))
        invoice_form.purchase_id = order
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.post()

        # Check if something was posted in the price difference account
        price_diff_aml = self.env['account.move.line'].search([('account_id','=', self.price_diff_account.id)])
        self.assertEquals(len(price_diff_aml), 0, "No line should have been generated in the price difference account.")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id','=', self.stock_input_account.id)])
        self.assertEquals(len(input_aml), 2, "Only two lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        self.assertAlmostEquals(sum(input_aml.mapped('debit')), 90, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEquals(sum(input_aml.mapped('credit')), 90, "Total credit value on stock input account should be equal to the original PO price of the product.")
