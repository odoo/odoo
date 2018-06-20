# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime

from odoo.tests.common import TransactionCase
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
        })
        self.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
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
        self.product1.product_tmpl_id.cost_method = 'average'
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

        # the unit price of the stock move has been updated to the latest value
        self.assertEquals(move1.price_unit, 200)

        self.assertEquals(self.product1.stock_value, 2000)

    def test_standard_price_change_1(self):
        """ Confirm a purchase order and create the associated receipt, change the unit cost of the
        purchase order and the standard price of the product before validating the receipt, the
        value of the received goods should be set according to the last standard price.
        """
        self.product1.product_tmpl_id.cost_method = 'standard'

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

        # the unit price of the stock move has been updated to the latest value
        self.assertEquals(move1.price_unit, 12)

        self.assertEquals(self.product1.stock_value, 120)

    def test_change_currency_rate_average_1(self):
        """ Confirm a purchase order in another currency and create the associated receipt, change
        the currency rate, validate the receipt and then check that the value of the received goods
        is set according to the last currency rate.
        """
        usd_currency = self.env.ref('base.USD')
        self.env.user.company_id.currency_id = usd_currency.id

        eur_currency = self.env.ref('base.EUR')

        self.product1.product_tmpl_id.cost_method = 'average'

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
        price_unit_usd = po1.currency_id.compute(po1.order_line.price_unit, po1.company_id.currency_id, round=True)

        # the unit price of the move is the unit price of the purchase order line converted in
        # the company's currency
        self.assertAlmostEqual(move1.price_unit, price_unit_usd)

        # change the rate of the currency
        self.env['res.currency.rate'].create({
            'name': time.strftime('%Y-%m-%d'),
            'rate': 2.0,
            'currency_id': eur_currency.id,
            'company_id': po1.company_id.id,
        })
        eur_currency._compute_current_rate()
        price_unit_usd_new_rate = po1.currency_id.compute(po1.order_line.price_unit, po1.company_id.currency_id, round=False)

        # the new price_unit is lower than th initial because of the rate's change
        self.assertLess(price_unit_usd_new_rate, price_unit_usd)

        # the unit price on the stock move is not directly updated
        self.assertAlmostEqual(move1.price_unit, price_unit_usd)

        # validate the receipt
        res_dict = picking1.button_validate()
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id'))
        wizard.process()

        # the unit price of the stock move has been updated to the latest value
        self.assertAlmostEqual(move1.price_unit, price_unit_usd_new_rate)

        self.assertAlmostEqual(self.product1.stock_value, price_unit_usd_new_rate * 10, delta=0.1)

    def test_extra_move_fifo_1(self):
        """ Check that the extra move when over processing a receipt is correctly merged back in
        the original move.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'
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
        self.assertEqual(move1.product_qty, 15)
        self.assertEqual(self.product1.stock_value, 1500)

    def test_backorder_fifo_1(self):
        """ Check that the backordered move when under processing a receipt correctly keep the
        price unit of the original move.
        """
        self.product1.product_tmpl_id.cost_method = 'fifo'
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


class TestStockValuationWithCOA(AccountingTestCase):
    def setUp(self):
        super(TestStockValuationWithCOA, self).setUp()
        self.supplier_location = self.env.ref('stock.stock_location_suppliers')
        self.stock_location = self.env.ref('stock.stock_location_stock')
        self.partner_id = self.env.ref('base.res_partner_1')
        self.product1 = self.env.ref('product.product_product_8')
        Account = self.env['account.account']
        self.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
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

    def test_fifo_anglosaxon_return(self):
        self.env.user.company_id.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.cost_method = 'fifo'
        self.product1.product_tmpl_id.valuation = 'real_time'
        self.product1.product_tmpl_id.invoice_policy = 'delivery'
        price_diff_account = self.env['account.account'].create({
            'name': 'price diff account',
            'code': 'price diff account',
            'user_type_id': self.env.ref('account.data_account_type_current_assets').id,
        })
        self.product1.property_account_creditor_price_difference = price_diff_account

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

        invoice_po1 = self.env['account.invoice'].create({
            'partner_id': self.partner_id.id,
            'purchase_id': po1.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'type': 'in_invoice',
        })
        invoice_po1.purchase_order_change()
        invoice_po1.action_invoice_open()

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

        invoice_po2 = self.env['account.invoice'].create({
            'partner_id': self.partner_id.id,
            'purchase_id': po2.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'type': 'in_invoice',
        })
        invoice_po2.purchase_order_change()
        invoice_po2.action_invoice_open()

        # valuation of product1 should be 300
        self.assertEqual(self.product1.stock_value, 300)

        # return the second po
        stock_return_picking = self.env['stock.return.picking']\
            .with_context(active_ids=receipt_po2.ids, active_id=receipt_po2.ids[0])\
            .create({})
        stock_return_picking.product_return_moves.quantity = 10
        stock_return_picking_action = stock_return_picking.create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_lines[0].move_line_ids[0].qty_done = 10
        return_pick.do_transfer()

        # valuation of product1 should be 200 as the first items will be sent out
        self.assertEqual(self.product1.stock_value, 200)

        # create a credit note for po2
        creditnote_po2 = self.env['account.invoice'].create({
            'partner_id': self.partner_id.id,
            'purchase_id': po2.id,
            'account_id': self.partner_id.property_account_payable_id.id,
            'type': 'in_refund',
        })

        creditnote_po2.purchase_order_change()
        creditnote_po2.invoice_line_ids[0].quantity = 10
        creditnote_po2.action_invoice_open()

        # check the anglo saxon entries
        price_diff_entry = self.env['account.move.line'].search([('account_id', '=', price_diff_account.id)])
        self.assertEqual(price_diff_entry.credit, 100)
