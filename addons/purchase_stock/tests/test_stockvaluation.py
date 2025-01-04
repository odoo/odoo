# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch

import odoo
from odoo import fields, exceptions, Command
from odoo.tests import Form
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.stock.tests.common import TestStockCommon


class TestStockValuation(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.url_extract_rec_id_and_model = TestStockCommon.url_extract_rec_id_and_model
        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.partner_id = cls.env['res.partner'].create({
            'name': 'Wood Corner Partner',
            'company_id': cls.env.user.company_id.id,
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'Large Desk',
            'standard_price': 1299.0,
            'list_price': 1799.0,
            # Ignore tax calculations for these tests.
            'supplier_taxes_id': False,
            'is_storable': True,
            'categ_id': cls.env.ref('product.product_category_goods').id,
        })
        Account = cls.env['account.account']
        cls.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'StockValuation',
            'account_type': 'asset_current',
        })
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        cls.product1.categ_id.write({
            'property_valuation': 'real_time',
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
        })
        cls.env.ref('base.EUR').active = True

    def test_different_uom(self):
        """ Set a quantity to replenish via the "Buy" route
        where product_uom is different from purchase uom
        """

        self.env['ir.config_parameter'].sudo().set_param('stock.propagate_uom', False)

        # Create and set a new weight unit.
        kgm = self.env.ref('uom.product_uom_kgm')
        ap = self.env['uom.uom'].create({
            'name': 'Algerian Pounds',
            'relative_factor': 2.475,
            'relative_uom_id': kgm.id,
        })
        kgm_price = 100
        ap_price = kgm_price * ap.factor / kgm.factor

        self.product1.uom_id = ap
        self.product1.uom_po_id = kgm

        # Set vendor
        vendor = self.env['res.partner'].create(dict(name='The Replenisher'))
        supplierinfo = self.env['product.supplierinfo'].create({
            'partner_id': vendor.id,
            'price': kgm_price,
        })
        self.product1.seller_ids = [(4, supplierinfo.id, 0)]

        # Automated stock valuation
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'

        # Create a manual replenishment
        replenishment_uom_qty = 200
        replenish_wizard = self.env['product.replenish'].with_context(default_product_tmpl_id=self.product1.product_tmpl_id.id).create({
            'product_id': self.product1.id,
            'product_tmpl_id': self.product1.product_tmpl_id.id,
            'product_uom_id': ap.id,
            'quantity': replenishment_uom_qty,
            'warehouse_id': self.env['stock.warehouse'].search([('company_id', '=', self.env.user.id)], limit=1).id,
        })
        genrated_picking = replenish_wizard.launch_replenishment()
        links = genrated_picking.get("params", {}).get("links")
        url = links and links[0].get("url", "") or ""
        purchase_order_id, model_name = self.url_extract_rec_id_and_model(url)
        last_po_id = False
        if purchase_order_id and model_name:
            last_po_id = self.env[model_name].browse(int(purchase_order_id))

        order_line = last_po_id.order_line.search([('product_id', '=', self.product1.id)])
        self.assertEqual(order_line.product_qty,
            ap._compute_quantity(replenishment_uom_qty, kgm, rounding_method='HALF-UP'),
            'Quantities does not match')

        # Receive products
        last_po_id.button_confirm()
        picking = last_po_id.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = move.product_uom_qty
        move.picked = True
        picking.button_validate()

        self.assertEqual(move.stock_valuation_layer_ids.unit_cost,
            last_po_id.currency_id.round(ap_price),
            "Wrong Unit price")

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
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]

        # the unit price of the purchase order line is copied to the in move
        self.assertEqual(move1.price_unit, 100)

        # update the unit price on the purchase order line
        po1.order_line.price_unit = 200


        # validate the receipt
        picking1.button_validate()

        # the unit price of the valuationlayer used the latest value
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 200)

        self.assertEqual(self.product1.value_svl, 2000)

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
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 11.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]

        # the move's unit price reflects the purchase order line's cost even if it's useless when
        # the product's cost method is standard
        self.assertEqual(move1.price_unit, 11)

        # set a new standard price
        self.product1.product_tmpl_id.standard_price = 12

        # the unit price on the stock move is not directly updated
        self.assertEqual(move1.price_unit, 11)

        # validate the receipt
        picking1.button_validate()

        # the unit price of the valuation layer used the latest value
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 12)

        self.assertEqual(self.product1.value_svl, 120)

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
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]
        move1.quantity = 15
        move1.picked = True
        picking1.button_validate()

        # there should be only one move
        self.assertEqual(len(picking1.move_ids), 1)
        self.assertEqual(move1.price_unit, 100)
        self.assertEqual(move1.stock_valuation_layer_ids.unit_cost, 100)
        self.assertEqual(move1.product_qty, 10)
        self.assertEqual(move1.quantity, 15)
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
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]
        move1.quantity = 5
        move1.picked = True
        res_dict = picking1.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
        wizard.process()

        self.assertEqual(len(picking1.move_ids), 1)
        self.assertEqual(move1.price_unit, 100)
        self.assertEqual(move1.product_qty, 5)

        picking2 = po1.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        self.assertEqual(len(picking2.move_ids), 1)
        self.assertEqual(move2.price_unit, 100)
        self.assertEqual(move2.product_qty, 5)


@tagged('post_install', '-at_install')
class TestStockValuationWithCOA(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.partner_id = cls.env['res.partner'].create({'name': 'Wood Corner Partner'})

        cls.cat = cls.env['product.category'].create({
            'name': 'cat',
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'categ_id': cls.cat.id,
        })
        cls.product1_copy = cls.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'categ_id': cls.cat.id,
        })

        Account = cls.env['account.account']
        cls.usd_currency = cls.env.ref('base.USD')
        cls.eur_currency = cls.env.ref('base.EUR')
        cls.usd_currency.active = True
        cls.eur_currency.active = True

        cls.stock_input_account = Account.create({
            'name': 'Stock Input',
            'code': 'StockIn',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.stock_output_account = Account.create({
            'name': 'Stock Output',
            'code': 'StockOut',
            'account_type': 'asset_current',
            'reconcile': True,
        })
        cls.stock_valuation_account = Account.create({
            'name': 'Stock Valuation',
            'code': 'StockValuation',
            'account_type': 'asset_current',
        })
        cls.price_diff_account = Account.create({
            'name': 'price diff account',
            'code': 'priceDiffAccount',
            'account_type': 'asset_current',
        })
        cls.stock_journal = cls.env['account.journal'].create({
            'name': 'Stock Journal',
            'code': 'STJTEST',
            'type': 'general',
        })
        cls.product1.categ_id.write({
            'property_stock_account_input_categ_id': cls.stock_input_account.id,
            'property_stock_account_output_categ_id': cls.stock_output_account.id,
            'property_stock_valuation_account_id': cls.stock_valuation_account.id,
            'property_stock_journal': cls.stock_journal.id,
            'property_account_creditor_price_difference_categ': cls.product1.product_tmpl_id.get_product_accounts()['expense'],
            'property_valuation': 'real_time',
        })

        old_action_post = odoo.addons.account.models.account_move.AccountMove.action_post
        old_create = odoo.models.BaseModel.create

        def new_action_post(self):
            """ Force the creation of tracking values. """
            res = old_action_post(self)
            if self:
                cls.env.flush_all()
                cls.cr.flush()
            return res

        def new_create(self, vals_list):
            cls.cr._now = datetime.now()
            return old_create(self, vals_list)

        post_patch = patch('odoo.addons.account.models.account_move.AccountMove.action_post', new_action_post)
        create_patch = patch('odoo.models.BaseModel.create', new_create)
        cls.startClassPatcher(post_patch)
        cls.startClassPatcher(create_patch)

    @classmethod
    def default_env_context(cls):
        # OVERRIDE
        return {}

    def _bill(self, po, qty=None, price=None):
        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.invoice_date = fields.Date.today()
        if qty is not None:
            bill.invoice_line_ids.quantity = qty
        if price is not None:
            bill.invoice_line_ids.price_unit = price
        bill.action_post()
        return bill

    def _refund(self, inv, qty=None):
        ctx = {'active_ids': inv.ids, 'active_model': 'account.move'}
        credit_note_wizard = self.env['account.move.reversal'].with_context(ctx).create({
            'journal_id': inv.journal_id.id,
        })
        rinv = self.env['account.move'].browse(credit_note_wizard.refund_moves()['res_id'])
        if qty is not None:
            rinv.invoice_line_ids.quantity = qty
        rinv.action_post()
        return rinv

    def _return(self, picking, qty=None):
        wizard_form = Form(self.env['stock.return.picking'].with_context(active_ids=picking.ids, active_id=picking.id, active_model='stock.picking'))
        wizard = wizard_form.save()
        qty = qty or picking.move_ids.quantity
        for line in wizard.product_return_moves:
            line.quantity = qty
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action["res_id"])
        return_picking.move_ids.move_line_ids.quantity = qty
        return_picking.move_ids.picked = True
        return_picking.button_validate()
        return return_picking

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
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()

        picking1 = po1.picking_ids[0]
        move1 = picking1.move_ids[0]

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
        picking1.button_validate()

        # the unit price of the valuation layer used the latest value
        self.assertAlmostEqual(move1.stock_valuation_layer_ids.unit_cost, price_unit_usd_new_rate)

        self.assertAlmostEqual(self.product1.value_svl, price_unit_usd_new_rate * 10, delta=0.1)

    def test_fifo_anglosaxon_return(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # Receive 10@10 ; create the vendor bill
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 10.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()
        receipt_po1 = po1.picking_ids[0]
        receipt_po1.move_ids.quantity = 10
        receipt_po1.move_ids.picked = True
        receipt_po1.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_id
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po1.id)
        invoice_po1 = move_form.save()
        invoice_po1.action_post()

        # Receive 10@20 ; create the vendor bill
        po2 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 10.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 20.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po2.button_confirm()
        receipt_po2 = po2.picking_ids[0]
        receipt_po2.move_ids.quantity = 10
        receipt_po2.move_ids.picked = True
        receipt_po2.button_validate()

        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_id
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po2.id)
        invoice_po2 = move_form.save()
        invoice_po2.action_post()

        # valuation of product1 should be 300
        self.assertEqual(self.product1.value_svl, 300)

        # return the second po
        stock_return_picking_form = Form(self.env['stock.return.picking'].with_context(
            active_ids=receipt_po2.ids, active_id=receipt_po2.ids[0], active_model='stock.picking'))
        stock_return_picking = stock_return_picking_form.save()
        stock_return_picking.product_return_moves.quantity = 10
        stock_return_picking_action = stock_return_picking.action_create_returns()
        return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
        return_pick.move_ids[0].move_line_ids[0].quantity = 10
        return_pick.move_ids[0].picked = True
        return_pick.button_validate()

        # valuation of product1 should be 200 as the first items will be sent out
        self.assertEqual(self.product1.value_svl, 200)
        # create a credit note for po2
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_refund'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = self.partner_id

        # Not supposed to see/change the purchase order of a refund invoice by default
        # <field name="purchase_id" invisible="1"/>
        # <label for="purchase_vendor_bill_id" string="Auto-Complete" class="oe_edit_only"
        #         invisible="state != 'draft' or move_type != 'in_invoice'" />
        # <field name="purchase_vendor_bill_id" nolabel="1"
        #         invisible="state != 'draft' or move_type != 'in_invoice'"
        move_form._view['modifiers']['purchase_id']['invisible'] = 'False'
        move_form.purchase_id = po2
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.quantity = 10
        creditnote_po2 = move_form.save()
        creditnote_po2.action_post()

        # check the anglo saxon entries
        price_diff_entry = self.env['account.move.line'].search([
            ('account_id', '=', self.stock_valuation_account.id),
            ('move_id.stock_move_id', '=', return_pick.move_ids[0].id)])
        self.assertEqual(price_diff_entry.credit, 100)

    def test_anglosaxon_valuation(self):
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

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
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        receipt_aml = stock_valuation_aml[0]
        self.assertEqual(len(stock_valuation_aml), 1, "For now, only one line for the stock valuation account")
        self.assertAlmostEqual(receipt_aml.debit, 10, msg="Should be equal to the PO line unit price (10)")

        # Create an invoice with a different price
        move_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        move_form.invoice_date = move_form.date
        move_form.partner_id = order.partner_id
        move_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with move_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 15.0
        invoice = move_form.save()
        invoice.action_post()

        # Check what was posted in the stock valuation account
        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        price_diff_aml = stock_valuation_aml - receipt_aml
        self.assertEqual(len(stock_valuation_aml), 2, "A second line should have been generated for the price difference.")
        self.assertAlmostEqual(price_diff_aml.debit, 5, msg="Price difference should be equal to 5 (15-10)")
        self.assertAlmostEqual(
            sum(stock_valuation_aml.mapped('debit')), 15,
            msg="Total debit value on stock valuation account should be equal to the invoiced price of the product.")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3, "Only three lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        invoice_amls = input_aml.filtered(lambda l: l.move_id == invoice)
        picking_aml = input_aml - invoice_amls
        self.assertEqual(sum(invoice_amls.mapped('debit')), 15, "Total debit value on stock input account should be equal to the invoice price of the product.")
        self.assertEqual(sum(invoice_amls.mapped('credit')), 0, "Invoice account move lines should not contains information on stock input at this point.")
        self.assertEqual(sum(picking_aml.mapped('credit')), 15, "Total credit value on stock input account should be equal to the invoice price of the product.")

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
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # Receive 10@10 ; create the vendor bill
        po1 = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'taxes_id': [(4, tax_with_no_account.id)],
                    'product_qty': 10.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 10.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po1.button_confirm()
        receipt_po1 = po1.picking_ids[0]
        receipt_po1.move_ids.quantity = 10
        receipt_po1.move_ids.picked = True
        receipt_po1.button_validate()

        # valuation of product1 should be 15 as the tax with no account set
        # has gone to the stock account, and must be reflected in inventory valuation
        self.assertEqual(self.product1.value_svl, 150)

    def test_standard_valuation_multicurrency(self):
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        date_po = '2019-01-01'

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'standard'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.standard_price = 10

        # SetUp currency and rates   1$ = 2 Euros
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
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # Create PO
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0, # 50$
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        # Receive the goods
        receipt = po.picking_ids[0]
        receipt.move_line_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create a vendor bill
        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
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

        inv.action_post()

        # Check what was posted in stock input account
        input_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_amls), 3, "Only three lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        invoice_amls = input_amls.filtered(lambda l: l.move_id == inv)
        picking_aml = input_amls - invoice_amls
        payable_aml = invoice_amls.filtered(lambda l: l.amount_currency > 0)
        diff_aml = invoice_amls - payable_aml

        # check USD
        self.assertAlmostEqual(payable_aml.debit, 50, msg="Total debit value should be equal to the original PO price of the product.")
        self.assertAlmostEqual(picking_aml.credit, 10, msg="credit value for stock should be equal to the standard price of the product.")
        self.assertAlmostEqual(diff_aml.credit, 40, msg="credit value for price difference")

        # check EUR
        self.assertAlmostEqual(payable_aml.amount_currency, 100, msg="Total debit value should be equal to the original PO price of the product.")
        self.assertAlmostEqual(picking_aml.amount_currency, -20, msg="credit value for stock should be equal to the standard price of the product.")
        self.assertAlmostEqual(diff_aml.amount_currency, -80, msg="credit value for price difference")

    def test_bill_on_ordered_qty_valuation_multicurrency(self):
        """
            Product with an invoice policy on ordered quantity should keep the valuation
            of the bill with the exchange rate at the bill date
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        date_po = '1993-07-18'

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.purchase_method = 'purchase'

        self.env['res.currency.rate'].create([{
            'name': date_po,
            'rate': 1 / 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        }])

        # Create PO
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,  # 100€ = 150$
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        # Create and post the vendor bill before recieving the product
        self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_po,
            'date': date_po,
            'currency_id': self.usd_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'price_unit': 100.0,  # 100$
                'product_id': self.product1.id,
                'purchase_line_id': po.order_line.id,
                'quantity': 1.0,
                'account_id': self.stock_input_account.id,
            })]
        }).action_post()

        receipt = po.picking_ids
        receipt.move_ids.picked = True
        receipt.button_validate()

        product_aml = po.invoice_ids.line_ids.filtered('product_id')
        self.assertEqual(receipt.move_ids.stock_valuation_layer_ids.value, 100)
        self.assertTrue(product_aml.reconciled)
        self.assertTrue(product_aml.full_reconcile_id)

    def test_valuation_rounding(self):
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        self.env.ref('product.decimal_price').digits = 5

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1500.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 3.30125,
                }),
            ],
        })
        po.button_confirm()

        # Receive the goods
        receipt = po.picking_ids
        receipt.button_validate()

        self._bill(po)
        layers = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(layers), 1)
        self.assertEqual(layers.quantity, 1500)
        self.assertEqual(layers.value, 4951.88)

    def test_valuation_rounding_price_diff(self):
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        self.env.ref('product.decimal_price').digits = 5

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1500.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 3.30125,
                }),
            ],
        })
        po.button_confirm()

        # Receive the goods
        receipt = po.picking_ids
        receipt.button_validate()

        self._bill(po, price=3.31125)
        layers = self.env['stock.valuation.layer'].search([('product_id', '=', self.product1.id)])
        self.assertEqual(len(layers), 2)
        self.assertEqual(layers[0].quantity, 1500)
        self.assertEqual(layers[1].quantity, 0)
        self.assertEqual(layers[0].value, 4951.88)
        self.assertEqual(round(layers[1].value, company.currency_id.decimal_places), 15)

    def test_valuation_multicurrency_with_tax(self):
        """ Check that the amount_currency does not include the tax.
        """

        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        date_po = '2019-01-01'

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # SetUp currency and rates 1$ = 2Euros
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })
        self.env['res.currency.rate'].create({
            'name': date_po,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        repartition_line_vals = [
            (0, 0, {"repartition_type": "base"}),
            (0, 0, {
                "factor_percent": 100,
                "repartition_type": "tax",
                "account_id": self.company_data['default_account_tax_sale'].id,
            }),
        ]
        tax = self.env['account.tax'].create({
            "name": "Tax with no account",
            "amount_type": "percent",
            "amount": 5,
            "price_include_override": "tax_included",
            "invoice_repartition_line_ids": repartition_line_vals,
            "refund_repartition_line_ids": repartition_line_vals,
        })

        # Create PO
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 105.0,  # 50$
                    'taxes_id': [(4, tax.id)],
                    'date_planned': date_po,
                }),
            ],
        })

        po.button_confirm()

        # Receive the goods
        receipt = po.picking_ids[0]
        receipt.move_line_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # empty stock to generate the AML values for the already out quantities
        inventory_quant = self.env['stock.quant'].sudo().search([
            ('location_id', '=', receipt.location_dest_id.id),
            ('product_id', '=', self.product1.id),
        ])
        inventory_quant.inventory_quantity = 0
        inventory_quant.action_apply_inventory()

        # Create a vendor bill
        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date_po,
            'date': date_po,
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'Test',
                'price_unit': 105.0,
                'product_id': self.product1.id,
                'purchase_line_id': po.order_line.id,
                'tax_ids': [(4, tax.id)],
                'quantity': 1.0,
                'account_id': self.stock_input_account.id,
            })]
        })

        inv.action_post()

        invoice_aml = inv.invoice_line_ids
        self.assertEqual(len(inv.line_ids), 3)
        picking_am = receipt.move_ids.stock_valuation_layer_ids.account_move_id.ensure_one()
        picking_aml = picking_am.line_ids.filtered(lambda line: line.account_id.id == self.stock_valuation_account.id)

        # check EUR
        self.assertAlmostEqual(invoice_aml.amount_currency, 100, msg="Total debit value should be equal to the original PO price of the product.")
        self.assertAlmostEqual(picking_aml.amount_currency, 100, msg="credit value for stock should be equal to the untaxed price of the product.")

    def test_valuation_multicurrency_with_tax_without_account(self):
        """ Similar test as test_valuation_multicurrency_with_tax, but without the accounts in the tax.
        Tax without accounts will increment the stock value (check test_valuation_from_increasing_tax).
        In this test, we verify that the amount_currency is also impacted by these changes.
        """

        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        # SetUp currency and rates 1$ = 2Euros
        self.env['res.currency.rate'].create({'currency_id': self.usd_currency.id, 'rate': 1})
        self.env['res.currency.rate'].create({'currency_id': self.eur_currency.id, 'rate': 2})

        tax_without_account = self.env['account.tax'].create({
            "name": "Tax with no account",
            "amount_type": "fixed",
            "amount": 5,
            "price_include_override": "tax_included",
        })

        # Create PO
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,  # 50$
                    'taxes_id': [(4, tax_without_account.id)],
                }),
            ],
        })

        po.button_confirm()

        # Receive the goods
        receipt = po.picking_ids[0]
        receipt.move_line_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        picking_am = receipt.move_ids.stock_valuation_layer_ids.account_move_id.ensure_one()
        picking_aml = picking_am.line_ids.filtered(lambda line: line.account_id.id == self.stock_valuation_account.id)

        self.assertAlmostEqual(picking_aml.amount_currency, 100, msg="The tax without account should be included in the stock value, and impact the amount_currency.")

    def test_average_realtime_anglo_saxon_valuation_multicurrency_same_date(self):
        """
        The PO and invoice are in the same foreign currency.
        The PO is invoiced on the same date as its creation.
        This shouldn't create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        date_po = '2019-01-01'

        # SetUp product
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
        self.product1.product_tmpl_id.purchase_method = 'purchase'

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
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
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
                'tax_ids': [],
            })]
        })

        inv.action_post()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 2)

        payable_line = move_lines.filtered(lambda l: l.account_id.account_type == 'liability_payable')

        self.assertEqual(payable_line.amount_currency, -100.0)
        self.assertAlmostEqual(payable_line.balance, -66.67)

        stock_line = move_lines.filtered(lambda l: l.account_id == self.stock_input_account and l.balance > 0)
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
        company.currency_id = self.usd_currency
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date_po = '2019-01-01'
        date_invoice = '2019-01-16'

        # SetUp product Average
        self.product1.product_tmpl_id.purchase_method = 'purchase'

        # SetUp product Standard
        # should have bought at 60 USD
        # actually invoiced at 70 EUR > 35 USD
        product_categ_standard = self.cat.copy({
            'property_cost_method': 'standard',
            'property_stock_account_input_categ_id': self.stock_input_account.id,
            'property_stock_account_output_categ_id': self.stock_output_account.id,
            'property_stock_valuation_account_id': self.stock_valuation_account.id,
            'property_stock_journal': self.stock_journal.id,
        })
        product_standard = self.product1_copy
        product_standard.write({
            'categ_id': product_categ_standard.id,
            'name': 'Standard Val',
            'standard_price': 60,
        })
        product_standard.product_tmpl_id.purchase_method = 'purchase'

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

        for patcher in patchers:
            self.startPatcher(patcher)

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': date_po,
                }),
                (0, 0, {
                    'name': product_standard.name,
                    'product_id': product_standard.id,
                    'product_qty': 1.0,
                    'product_uom_id': product_standard.uom_po_id.id,
                    'price_unit': 40.0,
                    'date_planned': date_po,
                }),
            ],
        })
        po.button_confirm()

        line_product_average = po.order_line.filtered(lambda l: l.product_id == self.product1)
        line_product_standard = po.order_line.filtered(lambda l: l.product_id == product_standard)

        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
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
                    'tax_ids': [],
                }),
                (0, 0, {
                    'name': product_standard.name,
                    'price_subtotal': 70.0,
                    'price_unit': 70.0,
                    'product_id': product_standard.id,
                    'purchase_line_id': line_product_standard.id,
                    'quantity': 1.0,
                    'account_id': self.stock_input_account.id,
                    'tax_ids': [],
                })
            ]
        })

        inv.action_post()

        move_lines = inv.line_ids
        self.assertEqual(len(move_lines), 3)

        # Ensure no exchange difference move has been created
        self.assertTrue(all([not l.reconciled for l in move_lines]))

        # PAYABLE CHECK
        payable_line = move_lines.filtered(lambda l: l.account_id.account_type == 'liability_payable')
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
        self.assertAlmostEqual(sum(stock_lines.mapped('amount_currency')), 70.00)
        self.assertAlmostEqual(sum(stock_lines.mapped('balance')), 35.00)

        # TODO It should be evaluated during the receiption now
        # price_diff_line = product_lines.filtered(lambda l: l.account_id == self.stock_valuation_account)
        # self.assertEqual(price_diff_line.amount_currency, -50.00)
        # self.assertAlmostEqual(price_diff_line.balance, -25.00)

    def test_average_realtime_with_delivery_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The delivery occurs in between PO validation and invoicing
        The invoice is created at an even different date
        This should create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date_po = '2019-01-01'
        date_delivery = '2019-01-08'
        date_invoice = '2019-01-16'

        product_avg = self.product1_copy
        product_avg.write({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 60,
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

        # To allow testing validation of PO and Delivery
        today = date_po

        def _today(*args, **kwargs):
            return datetime.strptime(today, "%Y-%m-%d").date()

        def _now(*args, **kwargs):
            return datetime.strptime(today + ' 01:00:00', "%Y-%m-%d %H:%M:%S")

        patchers = [
            patch('odoo.fields.Date.context_today', _today),
            patch('odoo.fields.Datetime.now', _now),
        ]

        for patcher in patchers:
            self.startPatcher(patcher)

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_avg.name,
                    'product_id': product_avg.id,
                    'product_qty': 1.0,
                    'product_uom_id': product_avg.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': date_po,
                })
            ],
        })
        po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)

        today = date_delivery
        picking = po.picking_ids
        (picking.move_ids
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity': 1.0, 'picked': True}))

        picking.button_validate()
        # 5 Units received at rate 0.7 = 42.86
        self.assertAlmostEqual(product_avg.standard_price, 42.86)

        today = date_invoice
        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
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
                    'tax_ids': [],
                })
            ]
        })

        inv.action_post()

        self.assertRecordValues(inv.line_ids, [
            # pylint: disable=C0326
            {'balance': 15.0,   'amount_currency': 30.0,    'account_id': self.stock_input_account.id},
            {'balance': -15.0,  'amount_currency': -30.0,   'account_id': self.company_data['default_account_payable'].id},
        ])
        self.assertRecordValues(inv.line_ids.full_reconcile_id.reconciled_line_ids.sorted('balance'), [
            # pylint: disable=C0326
            {'balance': -42.86, 'amount_currency': -30.0,   'account_id': self.stock_input_account.id},
            {'balance': 15.0,   'amount_currency': 30.0,    'account_id': self.stock_input_account.id},
            {'balance': 27.86,  'amount_currency': 0.0,     'account_id': self.stock_input_account.id},
        ])
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3)

    def test_average_realtime_with_delivery_anglo_saxon_valuation_multicurrency_same_dates(self):
        """ Same than test_average_realtime_with_delivery_anglo_saxon_valuation_multicurrency_different_dates
        but the rates change happens
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'

        date = fields.Date.to_string(fields.Date.today())

        product_avg = self.product1_copy
        product_avg.write({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 60,
        })

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create({
            'name': date,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        })

        eur_rate = self.env['res.currency.rate'].create({
            'name': date,
            'rate': 0.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        })

        # Proceed
        po = self.env['purchase.order'].create({
            'currency_id': self.eur_currency.id,
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': product_avg.name,
                    'product_id': product_avg.id,
                    'product_qty': 1.0,
                    'product_uom_id': product_avg.uom_po_id.id,
                    'price_unit': 30.0,
                    'date_planned': date,
                })
            ],
        })
        po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)
        picking = po.picking_ids
        (picking.move_ids
            .filtered(lambda l: l.purchase_line_id == line_product_avg)
            .write({'quantity': 1.0, 'picked': True}))

        picking.button_validate()
        # 5 Units received at rate 2 = 42.86
        self.assertAlmostEqual(product_avg.standard_price, 60)

        eur_rate.rate = 0.25

        inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
            'move_type': 'in_invoice',
            'invoice_date': date,
            'date': date,
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
                    'tax_ids': [],
                })
            ]
        })
        self.env['stock.move'].invalidate_model()
        inv.action_post()
        self.assertRecordValues(inv.line_ids, [
            # pylint: disable=C0326
            {'balance': 120.0,  'amount_currency': 30.0,    'account_id': self.stock_input_account.id},
            {'balance': -120.0, 'amount_currency': -30.0,   'account_id': self.company_data['default_account_payable'].id},
        ])
        self.assertRecordValues(inv.line_ids.full_reconcile_id.reconciled_line_ids.sorted('id'), [
            # pylint: disable=C0326
            {'balance': -60.0,  'amount_currency': -30.0,   'account_id': self.stock_input_account.id},
            {'balance': 120.0,  'amount_currency': 30.0,    'account_id': self.stock_input_account.id},
            {'balance': -60.0,  'amount_currency': 0.0,     'account_id': self.stock_input_account.id},
        ])
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3)

    def test_average_realtime_with_two_delivery_anglo_saxon_valuation_multicurrency_different_dates(self):
        """
        The PO and invoice are in the same foreign currency.
        The deliveries occur at different times and rates
        The invoice is created at an even different date
        This should create a price difference entry.
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        date_po = '2019-01-01'
        date_delivery = '2019-01-08'
        date_delivery1 = '2019-01-16'
        date_invoice = '2019-01-10'
        date_invoice1 = '2019-01-20'

        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.categ_id.property_cost_method = 'average'
        product_avg = self.product1_copy
        product_avg.write({
            'purchase_method': 'purchase',
            'name': 'AVG',
            'standard_price': 0,
        })

        # SetUp currency and rates
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", (self.usd_currency.id, company.id))
        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create([{
            'name': date_po,
            'rate': 1.0,
            'currency_id': self.usd_currency.id,
            'company_id': company.id,
        }, {
            'name': date_po,
            'rate': 1.5,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        }, {
            'name': date_delivery,
            'rate': 0.7,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        }, {
            'name': date_delivery1,
            'rate': 0.8,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        }, {
            'name': date_invoice,
            'rate': 2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        }, {
            'name': date_invoice1,
            'rate': 2.2,
            'currency_id': self.eur_currency.id,
            'company_id': company.id,
        }])

        # Proceed
        with freeze_time(date_po):
            po = self.env['purchase.order'].create({
                'currency_id': self.eur_currency.id,
                'partner_id': self.partner_id.id,
                'date_order': date_po,
                'order_line': [
                    (0, 0, {
                        'name': product_avg.name,
                        'product_id': product_avg.id,
                        'product_qty': 10.0,
                        'product_uom_id': product_avg.uom_po_id.id,
                        'price_unit': 30.0,
                        'date_planned': date_po,
                    })
                ],
            })
            po.button_confirm()

        line_product_avg = po.order_line.filtered(lambda l: l.product_id == product_avg)

        with freeze_time(date_delivery):
            picking = po.picking_ids
            (picking.move_ids
                .filtered(lambda l: l.purchase_line_id == line_product_avg)
                .write({'quantity': 5.0, 'picked': True}))

            picking.button_validate()
            picking._action_done()  # Create Backorder
        # 5 Units received at rate 0.7 = 42.86
        self.assertAlmostEqual(product_avg.standard_price, 42.86)

        with freeze_time(date_invoice):
            inv = self.env['account.move'].with_context(default_move_type='in_invoice').create({
                'move_type': 'in_invoice',
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
                        'tax_ids': [],
                    })
                ]
            })
            inv.action_post()
        # 5 Units invoiced at rate 2 instead of 0.7 and price unit 20 = 10
        self.assertAlmostEqual(product_avg.standard_price, 10)

        with freeze_time(date_delivery1):
            backorder_picking = self.env['stock.picking'].search([('backorder_id', '=', picking.id)])
            (backorder_picking.move_ids
                .filtered(lambda l: l.purchase_line_id == line_product_avg)
                .write({'quantity': 5.0, 'picked': True}))
            backorder_picking.button_validate()
        # 5 Units invoiced at rate 2 (10) + 5 Units received at rate 0.8 (37.50) = 23.75
        self.assertAlmostEqual(product_avg.standard_price, 23.75)

        with freeze_time(date_invoice1):
            inv1 = self.env['account.move'].with_context(default_move_type='in_invoice').create({
                'move_type': 'in_invoice',
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
                        'tax_ids': [],
                    })
                ]
            })
            inv1.action_post()
        # 5 Units invoiced at rate 2 (10) + 5 Units invoiced at rate 2.2 and unit price 40 (18.18) = 14.09
        self.assertAlmostEqual(product_avg.standard_price, 14.09)
        ##########################
        #       Invoice 0        #
        ##########################

        self.assertRecordValues(inv.line_ids, [
            # pylint: disable=C0326
            {'balance': 50.0,   'amount_currency': 100.0,   'account_id': self.stock_input_account.id},
            {'balance': -50.0,  'amount_currency': -100.0,  'account_id': self.company_data['default_account_payable'].id},
        ])

        ##########################
        #       Invoice 1        #
        ##########################

        self.assertRecordValues(inv1.line_ids, [
            # pylint: disable=C0326
            {'balance': 90.91,  'amount_currency': 200.0,   'account_id': self.stock_input_account.id},
            {'balance': -90.91, 'amount_currency': -200.0,  'account_id': self.company_data['default_account_payable'].id},
        ])

        ##########################
        #    Reconcile           #
        ##########################
        self.assertTrue(inv.line_ids.full_reconcile_id)
        self.assertTrue(inv1.line_ids.full_reconcile_id)
        self.assertRecordValues(inv.line_ids.full_reconcile_id.reconciled_line_ids.sorted('id'), [
            # pylint: disable=C0326
            {'balance': -214.29,    'amount_currency': -150.0},
            {'balance': 50,         'amount_currency': 100},
            {'balance': 164.29,     'amount_currency': 0.0},
            {'balance': 0.00,       'amount_currency': 50}
        ])
        self.assertRecordValues(inv1.line_ids.full_reconcile_id.reconciled_line_ids.sorted('id'), [
            # pylint: disable=C0326
            {'balance': -187.5,     'amount_currency': -150.0},
            {'balance': 90.91,      'amount_currency': 200.0},
            {'balance': 96.59,      'amount_currency': 0.0},
            {'balance': 0.00,       'amount_currency': -50.0},
        ])

    def test_anglosaxon_valuation_price_total_diff_discount(self):
        """
        PO:  price unit: 110
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

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
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # Check what was posted in the stock valuation account
        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        self.assertEqual(
            len(stock_valuation_aml), 2,
            "Two lines for the stock valuation account: one from the receipt (debit 110) and one from the bill (credit 20)")
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('debit')), 110)
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('credit')), 20, msg="Credit of 20 because of the difference between the PO and its invoice")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id','=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3, "Only two lines should have been generated in stock input account: one when receiving the product, two when making the invoice.")
        self.assertAlmostEqual(sum(input_aml.mapped('debit')), 110, msg="Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(input_aml.mapped('credit')), 110, msg="Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_discount(self):
        """
        PO:  price unit: 100
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

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
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.tax_ids.clear()
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # Check what was posted in the stock valuation account
        stock_valuation_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        self.assertEqual(len(stock_valuation_aml), 2, "Only one line should have been generated in the price difference account.")
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('debit')), 100)
        self.assertAlmostEqual(sum(stock_valuation_aml.mapped('credit')), 10, msg="Credit of 10 because of the 10% discount")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 3, "Three lines generated in stock input account: one when receiving the product, two when making the invoice.")
        self.assertAlmostEqual(sum(input_aml.mapped('debit')), 100, msg="Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(input_aml.mapped('credit')), 100, msg="Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_price_unit_diff_discount(self):
        """
        PO:  price unit:  90
        Inv: price unit: 100
             discount:    10
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

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
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        receipt.button_validate()

        # Create an invoice with a different price and a discount
        invoice_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        invoice_form.invoice_date = invoice_form.date
        invoice_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-order.id)
        with invoice_form.invoice_line_ids.edit(0) as line_form:
            line_form.price_unit = 100.0
            line_form.discount = 10.0
        invoice = invoice_form.save()
        invoice.action_post()

        # Check if something was posted in the price difference account
        price_diff_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        self.assertEqual(price_diff_aml.debit, 90, "Should have only one line in the stock valuation account, created by the receipt.")

        # Check what was posted in stock input account
        input_aml = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        self.assertEqual(len(input_aml), 2, "Only two lines should have been generated in stock input account: one when receiving the product, one when making the invoice.")
        self.assertAlmostEqual(sum(input_aml.mapped('debit')), 90, "Total debit value on stock input account should be equal to the original PO price of the product.")
        self.assertAlmostEqual(sum(input_aml.mapped('credit')), 90, "Total credit value on stock input account should be equal to the original PO price of the product.")

    def test_anglosaxon_valuation_price_unit_diff_avco(self):
        """
        Inv: price unit: 100
        """
        self.env.company.anglo_saxon_accounting = True
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.standard_price = 1.01

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'invoice_date': '2022-03-31',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [
                (0, 0, {'product_id': self.product1.id, 'quantity': 10.50, 'price_unit': 1.01, 'tax_ids': self.tax_purchase_a.ids})
            ]
        })

        # Check if something was posted in the stock valuation account.
        stock_val_aml = invoice.line_ids.filtered(lambda l: l.account_id == self.stock_valuation_account)
        self.assertEqual(len(stock_val_aml), 0, "No line should have been generated in the stock valuation account.")

    def test_price_diff_with_partial_bills_and_delivered_qties(self):
        """
        Fifo + Real time.
        Default UoM of the product is Unit.
        Company in USD. 1 USD = 2 EUR.
        Receive 10 Hundred @ $50:
            Receive 7 Hundred (R1)
            Receive 3 Hundred (R2)
        Deliver 5 Hundred
        Bill
            1 Hundred @ 120€ -> already out
            3 Hundred @ 120€ -> already out
            2 Hundred @ 120€ -> one is out, the other is in the stock
            4 Hundred @ 120€ -> nothing out
            When billing:
            - The already-delivered qty should not generate any SVL for the
            price difference and we should directly post some COGS entries
            - The in-stock qty should generate an SVL for the price difference,
            and we should post the journal entries related to that SVL
        Deliver 2 Hundred
            The SVL should include:
                - 2 x 50 (cost by hundred)
                - 2 x 10 (the price diff from step "Bill 2 Hundred @ 60" and "Bill
                          4 Hundred @ 60")
        On top of that, make sure that everything will still work if the option
        "Lock Posted Entries with Hash" is enabled on the stock journal
        """
        expected_svl_values = [] # USD
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref('stock.stock_location_customers')

        eur_curr = self.env.ref('base.EUR')
        self.env['res.currency.rate'].create({
            'name': fields.Date.today(),
            'company_id': self.env.company.id,
            'currency_id': eur_curr.id,
            'rate': 2,
        })

        grp_uom = self.env.ref('uom.group_uom')
        self.env.user.write({'groups_id': [(4, grp_uom.id)]})
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_hundred = self.env['uom.uom'].create({
            'name': '100 x U',
            'relative_factor': 100.0,
            'relative_uom_id': uom_unit.id,
        })
        self.product1.write({
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.categ_id.property_stock_journal.restrict_mode_hash_table = True

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 10
            po_line.product_uom_id = uom_hundred
            po_line.price_unit = 50.0
        po = po_form.save()
        po.button_confirm()

        # Receive 7 Hundred
        receipt01 = po.picking_ids[0]
        receipt01.move_ids.move_line_ids.quantity = 700
        receipt01.move_ids.picked = True
        action = receipt01.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save()
        backorder_wizard.process()

        expected_svl_values += [7 * 50]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)

        # Receive 3 Hundred
        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.picked = True
        receipt02.button_validate()

        expected_svl_values += [3 * 50]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)

        # Delivery 5 Hundred
        delivery01 = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 5,
                'product_uom': uom_hundred.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })],
            'state': 'draft',
        })
        delivery01.action_confirm()
        delivery01.move_ids.picked = True
        delivery01.button_validate()

        expected_svl_values += [-5 * 50]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)

        # We will create a price diff SVL only for the remaining quantities not yet billed
        # On the bill, price unit is 120€, i.e. $60 -> price diff equal to $10
        expense_account = self.company_data['default_account_expense']
        valuation_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id)])
        expense_amls = self.env['account.move.line'].search([('account_id', '=', expense_account.id)])
        input_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)])
        bills = self.env['account.move']
        # pylint: disable=bad-whitespace
        for qty,    new_svl_expected,       expected_valuations,    expected_expenses in [
            (1,     [],                     [],                     [10.0]),    # 1 hundred already out
            (3,     [],                     [],                     [30.0]),    # 3 hundred already out
            (2,     [1 * 10.0],             [10.0],                 [10.0]),    # 1 hundred already out and 1 hundred in stock (from R1)
            (4,     [1 * 10.0, 3 * 10.0],   [3 * 10.0, 1 * 10.0],   []),        # 4 hundred in stock, 1 from R1 and 3 from R2
        ]:
            bill_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
            bill_form.invoice_date = bill_form.date
            bill_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po.id)
            bill = bill_form.save()
            bill.invoice_line_ids.quantity = qty
            bill.invoice_line_ids.price_unit = 120.0
            bill.invoice_line_ids.product_uom_id = uom_hundred
            bill.currency_id = eur_curr
            bill.action_post()

            bills |= bill
            err_msg = 'Incorrect while billing %s hundred' % qty

            # stock side
            expected_svl_values += new_svl_expected
            self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values, err_msg)

            # account side
            new_valuation_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_valuation_account.id), ('id', 'not in', valuation_amls.ids)])
            new_expense_amls = self.env['account.move.line'].search([('account_id', '=', expense_account.id), ('id', 'not in', expense_amls.ids)])
            new_input_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id), ('id', 'not in', input_amls.ids)])
            valuation_amls |= new_valuation_amls
            expense_amls |= new_expense_amls
            input_amls |= new_input_amls

            self.assertEqual(new_valuation_amls.mapped('debit'), expected_valuations, err_msg)
            self.assertEqual(new_expense_amls.mapped('debit'), expected_expenses, err_msg)
            self.assertEqual(new_input_amls.filtered(lambda aml: aml.credit > 0).mapped('credit'), expected_expenses + expected_valuations, err_msg)
            self.assertEqual(new_input_amls.filtered(lambda aml: aml.debit > 0).debit, qty * 60, err_msg)

        # All AML of Stock Interim Receipt should be reconciled
        input_amls = bills.line_ids.filtered(lambda aml: aml.account_id == self.stock_input_account)
        full_reconcile = input_amls[0].full_reconcile_id
        self.assertTrue(full_reconcile)
        self.assertTrue(all(aml.full_reconcile_id == full_reconcile for aml in input_amls))

        # Delivery 2 Hundred
        delivery02 = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 2,
                'product_uom': uom_hundred.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })],
            'state': 'draft',
        })
        delivery02.action_confirm()
        delivery02.move_ids.picked = True
        delivery02.button_validate()

        expected_svl_values += [-2 * 50 + -2 * 10]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)

        svl_r01, svl_r02, _svl_d01, svl_diff_01, svl_diff_02, svl_diff_03, _svl_d02 = self.product1.stock_valuation_layer_ids
        self.assertEqual(svl_diff_01.stock_valuation_layer_id, svl_r01)
        self.assertEqual(svl_diff_02.stock_valuation_layer_id, svl_r01)
        self.assertEqual(svl_diff_03.stock_valuation_layer_id, svl_r02)

    def test_partial_bills_and_reconciliation(self):
        """
        Fifo, Auto
        Receive 5
        Deliver 5
        Bill 1 (with price diff)
        Bill 4 (with price diff)
        The lines in stock input account should be reconciled
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref('stock.stock_location_customers')

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 5
            po_line.price_unit = 50.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids[0]
        receipt.move_ids.picked = True
        receipt.button_validate()

        delivery = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 5,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })],
            'state': 'draft',
        })
        delivery.action_confirm()
        delivery.move_ids.picked = True
        delivery.button_validate()

        bill01_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        bill01_form.invoice_date = bill01_form.date
        bill01_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po.id)
        bill01 = bill01_form.save()
        bill01.invoice_line_ids.quantity = 1
        bill01.invoice_line_ids.price_unit = 60
        bill01.action_post()

        bill02_form = Form(self.env['account.move'].with_context(default_move_type='in_invoice'))
        bill02_form.invoice_date = bill02_form.date
        bill02_form.purchase_vendor_bill_id = self.env['purchase.bill.union'].browse(-po.id)
        bill02 = bill02_form.save()
        bill02.invoice_line_ids.quantity = 4
        bill02.invoice_line_ids.price_unit = 60
        bill02.action_post()

        input_amls = (bill01 + bill02).line_ids.filtered(lambda aml: aml.account_id == self.stock_input_account)
        full_reconcile = input_amls[0].full_reconcile_id
        self.assertTrue(full_reconcile)
        self.assertTrue(all(aml.full_reconcile_id == full_reconcile for aml in input_amls))

    def test_pdiff_and_credit_notes(self):
        """
        Auto FIFO
        PO 12 @ 10
        Receive with backorders: 4, 3 and then 5
            Will generate 3 SVL
        Bill:
            BILL01: 3 @ 12
            BILL02: 2 @ 11
            BILL03: 1 @ 15
            BILL04: 4 @ 9
            BILL05: 2 @ 10
            -: Refund 1 from BILL01
            -: Refund all from BILL02
            -: Refund 2 from BILL04
            -: Refund 1 from BILL05
            BILL06: 6 @ 18
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 12
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.move_line_ids.quantity = 4
        receipt01.move_ids.picked = True
        action = receipt01.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save()
        backorder_wizard.process()

        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.move_line_ids.quantity = 3
        receipt02.move_ids.picked = True
        action = receipt02.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save()
        backorder_wizard.process()

        receipt03 = receipt02.backorder_ids
        receipt03.move_ids.move_line_ids.quantity = 5
        receipt03.move_ids.picked = True
        receipt03.button_validate()

        expected_svl_values = [40, 30, 50]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)

        # pylint: disable=bad-whitespace
        for qty,    price,  expected_svl_values,                                expected_svl_remaining_values in [
            (3.0,   12.0,   [40.0, 30.0, 50.0, 6.0],                            [46.0, 30.0, 50.0, 0.0]),
            (2.0,   11.0,   [40.0, 30.0, 50.0, 6.0, 1.0, 1.0],                  [47.0, 31.0, 50.0, 0.0, 0.0, 0.0]),
            (1.0,   15.0,   [40.0, 30.0, 50.0, 6.0, 1.0, 1.0, 5.0],             [47.0, 36.0, 50.0, 0.0, 0.0, 0.0, 0.0]),
            (4.0,   9.0,    [40.0, 30.0, 50.0, 6.0, 1.0, 1.0, 5.0, -1.0, -3.0], [47.0, 35.0, 47.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            (2.0,   10.0,   [40.0, 30.0, 50.0, 6.0, 1.0, 1.0, 5.0, -1.0, -3.0], [47.0, 35.0, 47.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]:
            self._bill(po, qty, price)
            self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values, 'Err while invoicing %s @ %s' % (qty, price))
            self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values, 'Err while invoicing %s @ %s' % (qty, price))

        bill01, bill02, _bill03, bill04, bill05 = po.invoice_ids.sorted('id')

        self._refund(bill01, 1.0)
        expected_svl_values += [-2.0]
        expected_svl_remaining_values += [0.0]
        # should impact the first layer
        expected_svl_remaining_values[0] -= 2.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._refund(bill02)
        expected_svl_values += [-1.0, -1.0]
        expected_svl_remaining_values += [0.0, 0.0]
        # should impact the two first layers
        expected_svl_remaining_values[0] -= 1.0
        expected_svl_remaining_values[1] -= 1.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._refund(bill04, 2.0)
        expected_svl_values += [1.0, 1.0]
        expected_svl_remaining_values += [0.0, 0.0]
        # should impact the two last layers
        expected_svl_remaining_values[1] += 1.0
        expected_svl_remaining_values[2] += 1.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._refund(bill05, 1.0)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._bill(po, price=18.0)
        expected_svl_values += [16.0, 16.0, 16.0]
        expected_svl_remaining_values += [0.0, 0.0, 0.0]
        # should impact all layers
        expected_svl_remaining_values[0] += 16.0
        expected_svl_remaining_values[1] += 16.0
        expected_svl_remaining_values[2] += 16.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        accounts = self.product1.product_tmpl_id._get_product_accounts()
        stock_in_amls = self.env['account.move.line'].search([('account_id', '=', accounts['stock_input'].id)], order='id')
        self.assertRecordValues(stock_in_amls, [
            # Receipts
            {'debit': 0.0, 'credit': 40.0},
            {'debit': 0.0, 'credit': 30.0},
            {'debit': 0.0, 'credit': 50.0},
            # Bill01 3 @ 12
            {'debit': 36.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 6.0},
            # Bill02 2 @ 11
            {'debit': 22.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 1.0},
            {'debit': 0.0, 'credit': 1.0},
            # Bill03 1 @ 15
            {'debit': 15.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 5.0},
            # Bill04 4 @ 9
            {'debit': 36.0, 'credit': 0.0},
            {'debit': 1.0, 'credit': 0.0},
            {'debit': 3.0, 'credit': 0.0},
            # Bill05 2 @ 10
            {'debit': 20.0, 'credit': 0.0},
            # Refund 1 from BILL01
            {'debit': 0.0, 'credit': 12.0},
            {'debit': 2.0, 'credit': 0.0},
            # Refund all from BILL02
            {'debit': 0.0, 'credit': 22.0},
            {'debit': 1.0, 'credit': 0.0},
            {'debit': 1.0, 'credit': 0.0},
            # Refund 2 from BILL04
            {'debit': 0.0, 'credit': 18.0},
            {'debit': 0.0, 'credit': 1.0},
            {'debit': 0.0, 'credit': 1.0},
            # Refund 1 from BILL05
            {'debit': 0.0, 'credit': 10.0},
            # BILL06: 6 @ 18
            {'debit': 108.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 16.0},
            {'debit': 0.0, 'credit': 16.0},
            {'debit': 0.0, 'credit': 16.0},
        ])
        self.assertTrue(all(aml.full_reconcile_id for aml in stock_in_amls))

    def test_pdiff_with_credit_notes_and_delivered_qties(self):
        """
        Auto FIFO
        IN 10 @ 10
        Bill 10 @ 12
        OUT 3
        Full Refund
        Bill 10 @ 9
        OUT 1
        Full Refund
        Bill 10 @ 10
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        expected_svl_values = []
        expected_svl_remaining_values = []

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref('stock.stock_location_customers')

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 10
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 10
        receipt.move_ids.picked = True
        receipt.button_validate()
        expected_svl_values += [100.0]
        expected_svl_remaining_values += [100.0]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        bill01 = self._bill(po, price=12)
        expected_svl_values += [20.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] += 20.0  # should impact the layer of the receipt
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        delivery = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 3,
                'product_uom': self.product1.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })],
        })
        delivery.action_confirm()
        delivery.move_ids.quantity = 3.0
        delivery.move_ids.picked = True
        delivery.button_validate()
        expected_svl_values += [-36.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 36.0  # should impact the layer of the receipt
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._refund(bill01)
        expected_svl_values += [-14.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 14.0  # should impact the layer of the receipt
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        bill02 = self._bill(po, price=9)
        expected_svl_values += [-7.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 7.0  # should impact the layer of the receipt
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        delivery = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 1,
                'product_uom': self.product1.uom_id.id,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })],
        })
        delivery.action_confirm()
        delivery.move_ids.quantity = 1.0
        delivery.move_ids.picked = True
        delivery.button_validate()
        expected_svl_values += [-9.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 9.0  # should impact the layer of the receipt
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        ctx = {'active_ids': bill02.ids, 'active_model': 'account.move'}
        credit_note_wizard = self.env['account.move.reversal'].with_context(ctx).create({
            'journal_id': bill02.journal_id.id,
        })
        res_id = credit_note_wizard.modify_moves()['res_id']
        bill03 = self.env['account.move'].browse(res_id)
        bill03.invoice_date = fields.Date.today()
        bill03.invoice_line_ids.price_unit = 10.0
        bill03.action_post()
        # Impact of the refund (bill03 should not impact the SVLs since the unit price is the one of the POL)
        expected_svl_values += [6.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] += 6.0  # should impact the layer of the receipt
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        accounts = self.product1.product_tmpl_id._get_product_accounts()
        stock_in_amls = self.env['account.move.line'].search([('account_id', '=', accounts['stock_input'].id)], order='id')
        self.assertRecordValues(stock_in_amls, [
            # IN 10 @ 10
            {'debit': 0.0, 'credit': 100.0},
            # Bill 10 @ 12
            {'debit': 120.0, 'credit': 0.0},
            {'debit': 0.0, 'credit': 20.0},
            # (OUT 3)
            # Refund: here, we skip the 3 products delivered in the meantime,
            #   i.e. we only compensate the on-hand quantity (hence the $14
            #   instead of $20)
            {'debit': 0.0, 'credit': 120.0},
            {'debit': 14.0, 'credit': 0.0},
            # Bill 10 @ 9
            {'debit': 90.0, 'credit': 0.0},
            {'debit': 3.0, 'credit': 0.0},
            {'debit': 7.0, 'credit': 0.0},
            # (OUT 1)
            # Refund: again, we skip the product delivered in the meantime.
            #   We have $3 which is the reversing entry of the inital bill
            #   and 6$ from the stock valuation correction
            {'debit': 0.0, 'credit': 90.0},
            {'debit': 0.0, 'credit': 3.0},
            {'debit': 0.0, 'credit': 6.0},
            # Bill 10 @ 10
            {'debit': 100.0, 'credit': 0},
        ])

        self.assertEqual(sum(stock_in_amls.mapped('debit')) - sum(stock_in_amls.mapped('credit')), -5,
                         "There should be a difference because of the skipped products while posting the refunds (see "
                         "comments in above `assertRecordValues`). The value is the sum of the price differences of each "
                         "delivery: 3 * $2 + 1 * $-1). The user will have to manually add some account entries to "
                         "balance the accounts")

    def test_pdiff_with_returns_and_credit_notes(self):
        """
        Auto FIFO
        IN 10 @ 10
        Return 3
        IN (Return) 3
        Bill 10 @ 12
            This step will impact 7 products of the first layer and 3 products
            of the last one (i.e. the second IN)
        Return 1
        Refund 1 (from PO)
        Return 5
        Refund 5 (from initial bill)
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        accounts = self.product1.product_tmpl_id._get_product_accounts()
        expected_svl_values = []
        expected_svl_remaining_values = []

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 10
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 10
        receipt.move_ids.picked = True
        receipt.button_validate()
        expected_svl_values += [100.0]
        expected_svl_remaining_values += [100.0]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        return01 = self._return(receipt, qty=3)
        expected_svl_values += [-30.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 30
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._return(return01)
        expected_svl_values += [30.0]
        expected_svl_remaining_values += [30.0]
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        bill = self._bill(po, price=12)
        # two new layers because we have 7 remaining products in the first in-layer and 3 in the second one
        expected_svl_values += [14.0, 6.0]
        expected_svl_remaining_values += [0.0, 0.0]
        expected_svl_remaining_values[0] += 14.0
        # `expected_svl_remaining_values[1]` is the return, it does not change
        expected_svl_remaining_values[2] += 6.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)
        stock_in_amls = self.env['account.move.line'].search([('account_id', '=', accounts['stock_input'].id)])
        self.assertTrue(stock_in_amls)
        self.assertTrue(all(aml.full_reconcile_id for aml in stock_in_amls))

        self._return(receipt, qty=1)
        expected_svl_values += [-12.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 12.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        refund = self._bill(po, price=12)
        self.assertEqual(refund.move_type, 'in_refund')
        stock_in_amls = self.env['account.move.line'].search([('account_id', '=', accounts['stock_input'].id)])
        self.assertTrue(stock_in_amls)
        self.assertTrue(all(aml.full_reconcile_id for aml in stock_in_amls))

        self._return(receipt, qty=5)
        expected_svl_values += [-60.0]
        expected_svl_remaining_values += [0.0]
        expected_svl_remaining_values[0] -= 60.0
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)

        self._refund(bill, qty=5)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('value'), expected_svl_values)
        self.assertEqual(self.product1.stock_valuation_layer_ids.mapped('remaining_value'), expected_svl_remaining_values)
        stock_in_amls = self.env['account.move.line'].search([('account_id', '=', accounts['stock_input'].id)], order='id')
        self.assertRecordValues(stock_in_amls, [
            # IN 10 @ 10
            {'debit': 0.0, 'credit': 100.0},
            # Return 3
            {'debit': 30.0, 'credit': 0.0},
            # IN (Return) 3
            {'debit': 0.0, 'credit': 30.0},
            # Bill 10 @ 12
            {'debit': 120, 'credit': 0.0},
            {'debit': 0.0, 'credit': 14.0},
            {'debit': 0.0, 'credit': 6.0},
            # Return 1
            {'debit': 12.0, 'credit': 0.0},
            # Refund 1
            {'debit': 0, 'credit': 12.0},
            # Return 5
            {'debit': 60.0, 'credit': 0.0},
            # Refund 5
            {'debit': 0.0, 'credit': 60.0},
        ])
        self.assertTrue(all(aml.full_reconcile_id for aml in stock_in_amls))

    def _test_pdiff_and_order_between_bills_common(self):
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 2
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.move_line_ids.quantity = 1
        receipt01.move_ids.picked = True
        action = receipt01.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save()
        backorder_wizard.process()

        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.move_line_ids.quantity = 1
        receipt02.move_ids.picked = True
        receipt02.button_validate()

        bill01 = self._bill(po, 1.0, 11)

        ctx = {'active_ids': bill01.ids, 'active_model': 'account.move'}
        credit_note_wizard = self.env['account.move.reversal'].with_context(ctx).create({
            'journal_id': bill01.journal_id.id,
        })
        refund = self.env['account.move'].browse(credit_note_wizard.refund_moves()['res_id'])

        action = po.action_create_invoice()
        bill02 = self.env["account.move"].browse(action["res_id"])
        bill02.invoice_date = fields.Date.today()
        bill02.invoice_line_ids.quantity = 1.0
        bill02.invoice_line_ids.price_unit = 12

        return po, refund, bill02

    def test_pdiff_and_aml_labels(self):
        """
        When posting the bill, if an AML has a pdiff, it should not change any
        label of the bill
        """
        self.product1.type = 'consu'
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product_b
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.move_line_ids.quantity = 1
        receipt01.button_validate()

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.invoice_date = fields.Date.today()
        label01, label02 = bill.invoice_line_ids.mapped('name')
        self.assertTrue(label01)
        self.assertTrue(label02)

        bill.invoice_line_ids.price_unit = 11.0
        bill.action_post()
        self.assertEqual(bill.invoice_line_ids.mapped('name'), [label01, label02])

    def test_pdiff_and_order_between_bills_01(self):
        """
        Auto fifo
        IN 1 @ 10 -> SVL01
        IN 1 @ 10 -> SVL02
        BILL01 1 @ 11
            Should impact SVL01
        Create draft Refund
        Create draft BILL02 1 @ 12
        Post Refund
        Post BILL02
            Should impact SVL01
        Bill03 1 @ 13
            Should impact SVL02
        """
        po, refund, bill02 = self._test_pdiff_and_order_between_bills_common()
        refund.action_post()
        bill02.action_post()
        self._bill(po, price=13)

        svls = self.product1.stock_valuation_layer_ids
        self.assertEqual(svls.mapped('remaining_value'), [12.0, 13.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(svls.mapped('value'), [10.0, 10.0, 1.0, -1.0, 2.0, 3.0])

    def test_pdiff_and_order_between_bills_02(self):
        """
        Auto fifo
        IN 1 @ 10 -> SVL01
        IN 1 @ 10 -> SVL02
        BILL01 1 @ 11
            Should impact SVL01
        Create draft Refund
        Create draft BILL02 1 @ 12
        Post BILL02
            Should impact SVL02
        Post Refund
        Bill03 1 @ 13
            Should impact SVL01
        """
        po, refund, bill02 = self._test_pdiff_and_order_between_bills_common()
        bill02.action_post()
        refund.action_post()
        self._bill(po, price=13)

        svls = self.product1.stock_valuation_layer_ids
        self.assertEqual(svls.mapped('remaining_value'), [13.0, 12.0, 0.0, 0.0, 0.0, 0.0])
        self.assertEqual(svls.mapped('value'), [10.0, 10.0, 1.0, 2.0, -1.0, 3.0])

    def test_pdiff_multi_curr_and_rates(self):
        """
        Company in USD.
        Today: 100 EUR = 150 USD
        One day ago: 100 EUR = 130 USD
        Two days ago: 100 EUR = 125 USD
        Buy and receive one auto-AVCO product at 100 EUR. Bill it with:
        - Bill date: two days ago (125 USD)
        - Accounting date: one day ago (130 USD)
        The value at bill date should be used for both bill value and price
        diff value.
        """
        usd_currency = self.env.ref('base.USD')
        eur_currency = self.env.ref('base.EUR')

        today = fields.Date.today()
        one_day_ago = today - timedelta(days=1)
        two_days_ago = today - timedelta(days=2)

        self.env.company.currency_id = usd_currency.id

        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create([{
            'name': day.strftime('%Y-%m-%d'),
            'rate': 1 / rate,
            'currency_id': eur_currency.id,
            'company_id': self.env.company.id,
        } for (day, rate) in [
            (today, 1.5),
            (one_day_ago, 1.3),
            (two_days_ago, 1.25),
        ]])

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'currency_id': eur_currency.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'taxes_id': False,
                }),
            ],
        })
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1.0
        receipt.button_validate()

        layer = receipt.move_ids.stock_valuation_layer_ids
        self.assertEqual(layer.value, 150)

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.invoice_date = two_days_ago
        bill.date = one_day_ago
        bill.action_post()

        pdiff_layer = layer.stock_valuation_layer_ids
        self.assertEqual(pdiff_layer.value, -25)
        self.assertEqual(layer.remaining_value, 125)

        in_stock_amls = self.env['account.move.line'].search([
            ('product_id', '=', self.product1.id),
            ('account_id', '=', self.stock_input_account.id),
        ], order='id')
        self.assertRecordValues(in_stock_amls, [
            # pylint: disable=bad-whitespace
            {'date': today,         'debit': 0,     'credit': 150,  'reconciled': True},
            {'date': one_day_ago,   'debit': 125,   'credit': 0,    'reconciled': True},
            {'date': one_day_ago,   'debit': 25,    'credit': 0,    'reconciled': True},
        ])

    def test_pdiff_lot_valuation(self):
        """
        use a product valuated by lot.
        Receipt some lots in the same purchase order, validate the picking
        create the bill with a price different from the PO. Check every layers
        for the lots have their own price difference correction layer.
        """

        self.cat.property_cost_method = 'average'
        product = self.env['product.product'].create({
            'name': 'product1',
            'is_storable': True,
            'tracking': 'serial',
            'categ_id': self.cat.id,
            'lot_valuated': True,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_qty': 3.0,
                    'product_uom_id': product.uom_po_id.id,
                    'price_unit': 100.0,
                    'taxes_id': False,
                }),
            ],
        })
        po.button_confirm()

        receipt = po.picking_ids
        i = 1
        for line in receipt.move_ids.move_line_ids:
            line.write({
                'lot_name': 'lot_' + str(i),
                'quantity': 1,
            })
            i += 1
        receipt.move_ids.picked = True
        receipt.button_validate()
        lots = receipt.move_line_ids.lot_id
        self.assertEqual(receipt.state, 'done')

        for lot in lots:
            self.assertEqual(lot.standard_price, 100)

        layers = receipt.move_ids.stock_valuation_layer_ids
        self.assertEqual(layers.mapped('value'), [100, 100, 100])

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.line_ids.price_unit = 150
        bill.invoice_date = fields.Date.today()
        bill.action_post()
        for lot in lots:
            self.assertEqual(lot.standard_price, 150)

        pdiff_layers = layers.stock_valuation_layer_ids
        self.assertRecordValues(pdiff_layers, [
            # pylint: disable=bad-whitespace
            {'quantity': 0, 'lot_id': lots[0].id, 'value': 50},
            {'quantity': 0, 'lot_id': lots[1].id, 'value': 50},
            {'quantity': 0, 'lot_id': lots[2].id, 'value': 50},
        ])

    def test_purchase_with_backorders_and_return_and_price_changes(self):
        """
        When you have multiples receipts associated to a Purchase Order, with 1 bill for each receipt,
            then each bill has an impact on its own receipt only, hence if I modify the price on Bill01,
            it will not have an effect on Receipt02.
        However, if we create a return for a portion of a receipt,
            the invoiced_qty will be higher than the received_qty. This could be iterpreted has the bill
            being done before the receipt, which is not the case.
        In this test, we ensure that if the Control Policy is 'On received quantities' (procure_method = 'receive'),
            we keep using the purchase price for the svl unit_cost even when invoiced_qty > received_qty.
        """
        self.product1.categ_id.property_cost_method = 'average'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.purchase_method = 'receive'  # ControlPolicy

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 100
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        def _validate_backorder(po, qty):
            picking = po.picking_ids.filtered(lambda p: p.state not in ['done', 'draft', 'cancel']).ensure_one()
            picking.move_ids.move_line_ids.quantity = qty
            picking.button_validate()
            # Validate picking with backorder
            res_dict = picking.button_validate()
            wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
            wizard.process()
            return picking

        receipt01 = _validate_backorder(po, 30)
        self.assertEqual(receipt01.move_ids.stock_valuation_layer_ids.ensure_one().value, 300.0)
        bill01 = self._bill(po, price=12)
        self.assertEqual(bill01.invoice_line_ids.stock_valuation_layer_ids.ensure_one().value, 60.0)

        receipt02 = _validate_backorder(po, 30)
        # Even though Bill01 updated the price for Receipt01, the layers of Receipt02 are not impacted.
        self.assertEqual(receipt02.move_ids.stock_valuation_layer_ids.ensure_one().value, 300.0)
        bill02 = self._bill(po, price=13)
        self.assertEqual(bill02.invoice_line_ids.stock_valuation_layer_ids.ensure_one().value, 90.0)

        # With the return, the invoiced qty > received qty,
        # this must NOT be interpreted as the invoice done before the picking (purchase_method = 'purchase')
        self._return(receipt02, qty=10)

        receipt03 = _validate_backorder(po, 30)
        # Like Receipt02 layers, Receipt03 layers should not be impacted by the previous price changes.
        self.assertEqual(receipt03.move_ids.stock_valuation_layer_ids.ensure_one().value, 300.0)

    def test_invoice_on_ordered_qty_with_backorder_and_different_currency_automated(self):
        """Create a PO with currency different from the company currency. Set the
        product to be invoiced on ordered quantities. Receive partially the products
        and create a backorder. Create an invoice for the ordered quantity. Then
        receive the backorder. Check if the valuation layer is correctly created.
        """
        usd_currency = self.env.ref('base.USD')
        self.env.company.currency_id = usd_currency.id
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'
        self.product1.purchase_method = 'purchase'

        price_unit_EUR = 100
        price_unit_USD = self.env.ref('base.EUR')._convert(price_unit_EUR, usd_currency, self.env.company, fields.Date.today(), round=False)
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'currency_id': self.env.ref('base.EUR').id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 12.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po.button_confirm()
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 10
        move.picked = True
        res_dict = picking.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
        wizard.process()
        self.assertAlmostEqual(move.stock_valuation_layer_ids.unit_cost, price_unit_USD)

        po.action_create_invoice()

        picking2 = po.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        move2.quantity = 2
        move2.picked = True
        picking2.button_validate()
        self.assertAlmostEqual(move2.stock_valuation_layer_ids.unit_cost, price_unit_USD)

    def test_invoice_on_ordered_qty_with_backorder_and_different_currency_manual(self):
        """Same test as test_invoice_on_ordered_qty_with_backorder_and_different_currency_automated with manual_periodic valuation
        Ensure that the absence of account_move_id on the layers does not generate an Exception
        """
        usd_currency = self.env.ref('base.USD')
        self.env.company.currency_id = usd_currency.id
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'manual_periodic'
        self.product1.purchase_method = 'purchase'

        price_unit_EUR = 100
        price_unit_USD = self.env.ref('base.EUR')._convert(price_unit_EUR, usd_currency, self.env.company, fields.Date.today(), round=False)
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'currency_id': self.env.ref('base.EUR').id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 12.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po.button_confirm()
        picking = po.picking_ids[0]
        move = picking.move_ids[0]
        move.quantity = 10
        move.picked = True
        res_dict = picking.button_validate()
        self.assertEqual(res_dict['res_model'], 'stock.backorder.confirmation')
        wizard = self.env[(res_dict.get('res_model'))].browse(res_dict.get('res_id')).with_context(res_dict['context'])
        wizard.process()
        self.assertAlmostEqual(move.stock_valuation_layer_ids.unit_cost, price_unit_USD)

        po.action_create_invoice()

        picking2 = po.picking_ids.filtered(lambda p: p.backorder_id)
        move2 = picking2.move_ids[0]
        move2.quantity = 2
        move2.picked = True
        picking2.button_validate()
        self.assertAlmostEqual(move2.stock_valuation_layer_ids.unit_cost, price_unit_USD)

    def test_pdiff_date_usererror(self):
        """
        Test pdiff operations complete without errors in case we don't have
        the bill date. A UserError is raised as usual.
        """
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'order_line': [
                (0, 0, {
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_qty': 1.0,
                    'product_uom_id': self.product1.uom_po_id.id,
                    'price_unit': 100.0,
                    'taxes_id': False,
                }),
            ],
        })
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1.0
        receipt.button_validate()

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        with self.assertRaises(exceptions.UserError):
            bill.action_post()

    def test_bill_date_exchange_rate_for_price_diff_amls(self):
        """Ensure sure that the amls for price difference uses the bill date exchange rate. They originally used today's rate
        which meant that their value depended on the day the bill was posted (as it is when the price diff amls are created).
        """
        company = self.env.user.company_id
        company.anglo_saxon_accounting = True
        company.currency_id = self.usd_currency

        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        po_date = '2023-10-01'
        bill_date = '2023-11-01'
        today = fields.Date.today()

        po_rate = 2.0
        bill_rate = 3.0
        today_rate = 4.0

        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create([
            {
                'name': po_date,
                'rate': po_rate,
                'currency_id': self.eur_currency.id,
                'company_id': company.id,
            },
            {
                'name': bill_date,
                'rate': bill_rate,
                'currency_id': self.eur_currency.id,
                'company_id': company.id,
            },
            {
                'name': today,
                'rate': today_rate,
                'currency_id': self.eur_currency.id,
                'company_id': company.id,
            },
        ])

        with freeze_time(po_date):
            purchase_price = 90
            po = self.env['purchase.order'].create({
                'partner_id': self.partner_id.id,
                'currency_id': self.eur_currency.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product1.id,
                        'product_qty': 1.0,
                        'price_unit': purchase_price,
                        'taxes_id': False,
                    }),
                ]
            })
            po.button_confirm()

            receipt = po.picking_ids
            receipt.move_line_ids.quantity = 1
            receipt.button_validate()

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company.id)], limit=1)
        stock_location = warehouse.lot_stock_id
        customer_location = self.env.ref('stock.stock_location_customers')
        delivery = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [
                Command.create({
                    'name': self.product1.name,
                    'product_id': self.product1.id,
                    'product_uom_qty': 1.0,
                    'location_id': stock_location.id,
                    'location_dest_id': customer_location.id,
                })
            ]
        })
        delivery.action_confirm()
        delivery.move_ids.quantity = 1.0
        delivery.button_validate()

        po.action_create_invoice()
        bill = po.invoice_ids
        bill.invoice_date = bill_date
        bill.action_post()

        product_accounts = self.product1.product_tmpl_id.get_product_accounts()
        payable_id = self.company_data['default_account_payable'].id
        stock_in_id = product_accounts['stock_input'].id
        expense_id = product_accounts['expense'].id
        self.assertRecordValues(bill.line_ids, [
            # pylint: disable=bad-whitespace
            {'debit': 30,   'credit': 0,    'account_id': stock_in_id,  'reconciled': True,     'amount_currency': 90},
            {'debit': 0,    'credit': 30,   'account_id': payable_id,   'reconciled': False,    'amount_currency': -90},
            {'debit': 0,    'credit': 15,   'account_id': expense_id,   'reconciled': False,    'amount_currency': 0},
            {'debit': 15,   'credit': 0,    'account_id': stock_in_id,  'reconciled': True,     'amount_currency': 0},
        ])

        stock_amls = self.env['account.move.line'].search([('account_id', '=', stock_in_id)])
        self.assertRecordValues(stock_amls, [
            # pylint: disable=bad-whitespace
            {'debit': 30,   'credit': 0,    'account_id': stock_in_id,  'reconciled': True, 'amount_currency': 90},
            {'debit': 15,   'credit': 0,    'account_id': stock_in_id,  'reconciled': True, 'amount_currency': 0},
            {'debit': 0,    'credit': 45,   'account_id': stock_in_id,  'reconciled': True, 'amount_currency': -90},
        ])

    def test_invoice_first_receipt_later_with_multicurrency_different_dates(self):
        """Ensure sure that use currency rate at bill date rather than the current date when invoice before receipt"""
        company = self.env.user.company_id
        company.anglo_saxon_accounting = False
        company.currency_id = self.usd_currency

        self.product1.is_storable = True
        self.product1.purchase_method = 'purchase'

        self.product1.with_company(company).categ_id.property_cost_method = 'fifo'
        self.product1.with_company(company).categ_id.property_valuation = 'real_time'


        po_date = '2023-10-01'
        bill_date = '2023-10-15'
        receipt_date = '2023-10-31'

        po_rate = 0.8
        bill_rate = 2.0
        receipt_rate = 2.2

        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create([
            {
                'name': po_date,
                'rate': po_rate,
                'currency_id': self.eur_currency.id,
                'company_id': company.id,
            },
            {
                'name': bill_date,
                'rate': bill_rate,
                'currency_id': self.eur_currency.id,
                'company_id': company.id,
            },
            {
                'name': receipt_date,
                'rate': receipt_rate,
                'currency_id': self.eur_currency.id,
                'company_id': company.id,
            },
        ])

        with freeze_time(po_date):
            purchase_price = 100
            po = self.env['purchase.order'].create({
                'partner_id': self.partner_id.id,
                'currency_id': self.eur_currency.id,
                'order_line': [
                    Command.create({
                        'product_id': self.product1.id,
                        'product_qty': 1.0,
                        'price_unit': purchase_price,
                        'taxes_id': False,
                    }),
                ]
            })
            po.button_confirm()

        with freeze_time(bill_date):
            po.action_create_invoice()
            bill = po.invoice_ids
            bill.invoice_date = bill_date
            bill.action_post()

        with freeze_time(receipt_date):
            receipt = po.picking_ids
            receipt.move_ids.write({'quantity': 1.0})
            receipt.button_validate()

        product_accounts = self.product1.product_tmpl_id.get_product_accounts()
        payable_id = self.company_data['default_account_payable'].id
        stock_in_id = product_accounts['stock_input'].id
        expense_id = product_accounts['expense'].id
        stock_valuation = product_accounts['stock_valuation'].id

        # 1 Units invoiced at rate 2 and unit price 100 = 50
        self.assertRecordValues(bill.line_ids, [
            # pylint: disable=bad-whitespace
            {'debit': 50.0,    'credit': 0,    'account_id': expense_id,   'reconciled': False,    'amount_currency':  100.0},
            {'debit': 0,        'credit': 50.0,  'account_id': payable_id,   'reconciled': False,    'amount_currency': -100.0},
        ])

        layer_receipt = receipt.move_ids.stock_valuation_layer_ids

        self.assertRecordValues(layer_receipt.account_move_id.line_ids, [
            # pylint: disable=bad-whitespace
            {'debit': 0,   'credit': 50.0,    'account_id': stock_in_id,  'reconciled': False, 'amount_currency': -110.0},
            {'debit': 50.0,   'credit': 0,    'account_id': stock_valuation,  'reconciled': False, 'amount_currency': 110.0},
        ])

    def test_analytic_distribution_propagation_with_exchange_difference(self):
        # Create 2 rates in order to generate an exchange difference later.
        eur = self.env.ref('base.EUR')
        eur.write({
            'rate_ids': [
                Command.clear(),
                Command.create({
                    'name': fields.Date.from_string('2023-01-01'),
                    'company_rate': 2.0,
                }),
                Command.create({
                    'name': fields.Date.from_string('2023-12-01'),
                    'company_rate': 3.0,
                }),
            ],
            'active': True,
        })

        # Create a mandatory analytic account.
        analytic_plan = self.env['account.analytic.plan'].create({
            'name': 'Analytic Plan',
            'default_applicability': 'mandatory',
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'Analytic Account',
            'plan_id': analytic_plan.id},
        )

        # Create a storable product with FIFO costing method and automated inventory valuation.
        analytic_product_category = self.env['product.category'].create({
            'name': 'Analytic Product Category',
            'property_cost_method': 'fifo',
            'property_valuation': 'real_time',
        })
        analytic_product = self.env['product.product'].create({
            'name': 'Analytic Product',
            'is_storable': True,
            'categ_id': analytic_product_category.id,
            'lst_price': 100.0,
            'standard_price': 25.0,
        })

        # Create and confirm a Purchase Order using aforementioned product and currency.
        purchase_order = self.env['purchase.order'].create({
            'date_order': fields.Date.from_string('2023-12-04'),
            'currency_id': eur.id,
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': analytic_product.id,
                    'product_qty': 10.0,
                    'analytic_distribution': {analytic_account.id: 100},
                }),
            ],
        })
        purchase_order.button_confirm()

        # Make sure a stock move has been created to replenish the product.
        self.assertEqual(len(purchase_order.picking_ids.move_ids), 1)

        stock_move = purchase_order.picking_ids.move_ids
        stock_move.quantity = stock_move.product_uom_qty

        purchase_order.picking_ids.button_validate()
        purchase_order.action_create_invoice()

        # Make sure a first Journal Entry has been created (to account for the stock move).
        self.assertEqual(len(stock_move.account_move_ids), 1)
        stock_account_move = stock_move.account_move_ids

        # Make sure the Vendor Bill has been created,
        # and confirm it at an earlier date (to generate the exchange difference).
        self.assertEqual(len(purchase_order.invoice_ids), 1)

        vendor_bill = purchase_order.invoice_ids
        vendor_bill.invoice_date = fields.Date.from_string('2023-11-01')
        vendor_bill.action_post()

        # Make sure a second Journal Entry has been created (to account for the exchange difference).
        self.assertEqual(len(stock_move.account_move_ids), 2)
        exchange_account_move = stock_move.account_move_ids - stock_account_move

        # Make sure both exchange Journal Items have the correct analytic distribution.
        self.assertEqual(len(exchange_account_move.line_ids), 2)
        for line in exchange_account_move.line_ids:
            self.assertTrue(line.analytic_distribution)
            self.assertEqual(line.analytic_distribution[str(analytic_account.id)], 100)

    def test_curr_rates_and_out_qty(self):
        """
        Company in USD
        Yesterday:  1000 EUR = 4335.1 USD
        Today:      1000 EUR = 4348.0 USD

        Yesterday: Buy and receive one auto-AVCO product at 1000 EUR
        Today:
        - Deliver the product
        - Bill the PO

        When posting the bill, we should generate an exchange diff compensation
        """
        usd_currency = self.env.ref('base.USD')
        eur_currency = self.env.ref('base.EUR')

        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        customer_location = self.env.ref('stock.stock_location_customers')
        stock_location = warehouse.lot_stock_id

        today = fields.Date.today()
        yesterday = today - timedelta(days=1)

        self.env.company.currency_id = usd_currency.id

        self.env['res.currency.rate'].search([]).unlink()
        self.env['res.currency.rate'].create([{
            'name': day.strftime('%Y-%m-%d'),
            'rate': 1 / rate,
            'currency_id': eur_currency.id,
            'company_id': self.env.company.id,
        } for (day, rate) in [
            (yesterday, 4.3351),
            (today, 4.3480),
        ]])

        self.product1.product_tmpl_id.categ_id.property_cost_method = 'average'

        with freeze_time(yesterday):
            po = self.env['purchase.order'].create({
                'partner_id': self.partner_id.id,
                'currency_id': eur_currency.id,
                'order_line': [
                    (0, 0, {
                        'name': self.product1.name,
                        'product_id': self.product1.id,
                        'product_qty': 1.0,
                        'product_uom_id': self.product1.uom_po_id.id,
                        'price_unit': 1000.0,
                        'taxes_id': False,
                    }),
                ],
            })
            po.button_confirm()

            receipt = po.picking_ids
            receipt.move_ids.move_line_ids.quantity = 1.0
            receipt.button_validate()

        delivery = self.env['stock.picking'].create({
            'location_id': stock_location.id,
            'location_dest_id': customer_location.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [(0, 0, {
                'name': self.product1.name,
                'product_id': self.product1.id,
                'product_uom_qty': 1.0,
                'location_id': stock_location.id,
                'location_dest_id': customer_location.id,
            })]
        })
        delivery.action_confirm()
        delivery.move_ids.quantity = 1.0
        delivery.button_validate()

        action = po.action_create_invoice()
        bill = self.env["account.move"].browse(action["res_id"])
        bill.invoice_date = bill.date = today
        bill.action_post()

        in_stock_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)], order='id')
        self.assertRecordValues(in_stock_amls, [
            # pylint: disable=bad-whitespace
            {'debit': 0,        'credit': 4335.1,   'reconciled': True},
            {'debit': 4348,     'credit': 0,        'reconciled': True},
            {'debit': 0,        'credit': 12.9,     'reconciled': True},
        ])

    def test_bill_with_zero_qty(self):
        """
        FIFO standard
        Receive two different product
        Bill them, but:
            Set the quantity of the first AML to zero
        Bill again the PO (for the "canceled" line in the first bill)
        """
        product1 = self.product1
        product2 = self.product1_copy

        self.cat.property_valuation = 'real_time'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        with po_form.order_line.new() as po_line:
            po_line.product_id = product2
            po_line.product_qty = 1
            po_line.price_unit = 20.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1
        receipt.button_validate()

        action = po.action_create_invoice()
        bill01 = self.env["account.move"].browse(action["res_id"])
        bill01.invoice_date = fields.Date.today()
        bill01.invoice_line_ids.filtered(lambda l: l.product_id == product2).quantity = 0
        bill01.action_post()

        self.assertEqual(bill01.state, 'posted')
        self.assertRecordValues(po.order_line, [
            {'product_id': product1.id, 'qty_invoiced': 1.0},
            {'product_id': product2.id, 'qty_invoiced': 0.0},
        ])

        bill02 = self._bill(po)
        self.assertEqual(bill02.state, 'posted')
        self.assertRecordValues(po.order_line, [
            {'product_id': product1.id, 'qty_invoiced': 1.0},
            {'product_id': product2.id, 'qty_invoiced': 1.0},
        ])

        stock_in_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id), ('balance', '!=', 0)], order='id')
        self.assertRecordValues(stock_in_amls, [
            {'product_id': product1.id, 'debit': 10.0, 'credit': 0.0},
            {'product_id': product1.id, 'debit': 0.0, 'credit': 10.0},
            {'product_id': product2.id, 'debit': 20.0, 'credit': 0.0},
            {'product_id': product2.id, 'debit': 0.0, 'credit': 20.0},
        ])
        self.assertTrue(all(aml.full_reconcile_id for aml in stock_in_amls))

    def _test_fifo_and_returns_common(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        """
        self.product1.categ_id.property_cost_method = 'fifo'
        self.product1.categ_id.property_valuation = 'real_time'

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()

        receipt = po.picking_ids
        receipt.move_ids.move_line_ids.quantity = 1
        receipt.button_validate()

        self._bill(po)

    def test_fifo_return_and_receive_all_on_backorder(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        PO 4 @ 25
        Receive one with backorder
        Return it
        Receive 4 thanks to the backorder
        Bill them
        """
        self._test_fifo_and_returns_common()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 4
            po_line.price_unit = 25.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        action = receipt01.button_validate()
        backorder_wizard = Form(self.env['stock.backorder.confirmation'].with_context(action['context'])).save()
        backorder_wizard.process()

        self._return(receipt01)

        receipt02 = receipt01.backorder_ids
        receipt02.move_ids.quantity = 4
        receipt02.button_validate()

        self._bill(po)

        in_stock_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)], order='id')
        self.assertRecordValues(in_stock_amls, [
            # Receive and bill 1 @ 10
            {'debit': 0.0, 'credit': 10.0, 'reconciled': True},
            {'debit': 10.0, 'credit': 0.0, 'reconciled': True},
            # Receive 1 @ 25
            {'debit': 0.0, 'credit': 25.0, 'reconciled': True},
            # Return it (10 with valo, 15 with expense)
            {'debit': 10.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 15.0, 'credit': 0.0, 'reconciled': True},
            # Receive all on the backorder (-> all based on PO price, we will not get the value of the returned one)
            {'debit': 0.0, 'credit': 100.0, 'reconciled': True},
            # Bill it
            {'debit': 100.0, 'credit': 0.0, 'reconciled': True},
        ])
        self.assertTrue(all(aml.full_reconcile_id for aml in in_stock_amls))

    def test_fifo_return_twice_and_bill(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        Receive 1 @ 25
        Return
        Receive it again
        Bill
        """
        self._test_fifo_and_returns_common()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 25.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        receipt01.button_validate()

        receipt01_return = self._return(receipt01)
        self._return(receipt01_return)
        self._bill(po)

        in_stock_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)], order='id')
        self.assertRecordValues(in_stock_amls, [
            # Receive and bill 1 @ 10
            {'debit': 0.0, 'credit': 10.0, 'reconciled': True},
            {'debit': 10.0, 'credit': 0.0, 'reconciled': True},
            # Receive 1 @ 25
            {'debit': 0.0, 'credit': 25.0, 'reconciled': True},
            # Return it (10 with valo, 15 with expense)
            {'debit': 10.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 15.0, 'credit': 0.0, 'reconciled': True},
            # Receive it again
            # The "return of a return" ignores the POL price and uses the value of the returned product
            # So, same: 10 with valo, 15 with expense
            {'debit': 0.0, 'credit': 10.0, 'reconciled': True},
            {'debit': 0.0, 'credit': 15.0, 'reconciled': True},
            # Bill it
            {'debit': 25.0, 'credit': 0.0, 'reconciled': True},
        ])
        self.assertTrue(all(aml.full_reconcile_id for aml in in_stock_amls))

    def test_fifo_bill_return_refund(self):
        """
        FIFO auto
        Receive & Bill 1 @ 10
        Receive 1 @ 25
        Bill
        Return
        Refund
        """
        self._test_fifo_and_returns_common()

        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = self.product1
            po_line.product_qty = 1
            po_line.price_unit = 25.0
        po = po_form.save()
        po.button_confirm()

        receipt01 = po.picking_ids
        receipt01.move_ids.quantity = 1
        receipt01.button_validate()

        self._bill(po)
        self._return(receipt01)
        self._bill(po)  # Refund

        in_stock_amls = self.env['account.move.line'].search([('account_id', '=', self.stock_input_account.id)], order='id')
        self.assertRecordValues(in_stock_amls, [
            # Receive and bill 1 @ 10
            {'debit': 0.0, 'credit': 10.0, 'reconciled': True},
            {'debit': 10.0, 'credit': 0.0, 'reconciled': True},
            # Receive 1 @ 25
            {'debit': 0.0, 'credit': 25.0, 'reconciled': True},
            # Bill
            {'debit': 25.0, 'credit': 0.0, 'reconciled': True},
            # Return (10 with valo, 15 with expense)
            {'debit': 10.0, 'credit': 0.0, 'reconciled': True},
            {'debit': 15.0, 'credit': 0.0, 'reconciled': True},
            # Refund
            {'debit': 0.0, 'credit': 25.0, 'reconciled': True},
        ])
        self.assertTrue(all(aml.full_reconcile_id for aml in in_stock_amls))

    def test_incoming_with_negative_qty(self):
        """
                FIFO/AVCO Auto
                Purchase one Product with negative qty
                Conform PO,
                It will create outgoing shipment
                        this transfer is neither returned nor received but it will be a delivery(outgoing).
                """
        product1 = self.product1
        self.cat.property_valuation = 'real_time'
        shipping_partner = self.env["res.partner"].create({
            'name': "Shipping Partner",
            'street': "234 W 18th Ave",
            'city': "Columbus",
            'state_id': self.env.ref("base.state_us_30").id,  # Ohio
            'country_id': self.env.ref("base.us").id,
            'zip': "43210",
        })
        po_form = Form(self.env['purchase.order'])
        po_form.partner_id = self.partner_id
        with po_form.order_line.new() as po_line:
            po_line.product_id = product1
            po_line.product_qty = -2
            po_line.price_unit = 10.0
        po = po_form.save()
        po.button_confirm()
        delivery = po.picking_ids
        # it is negative qty transfer so Odoo will create delivery instead of receipt.
        delivery.partner_id = shipping_partner
        move_line_vals = delivery.move_ids._prepare_move_line_vals()
        move_line = self.env['stock.move.line'].create(move_line_vals)
        move_line.quantity = 2.
        delivery.button_validate()
        self.assertEqual(delivery.state, 'done')
