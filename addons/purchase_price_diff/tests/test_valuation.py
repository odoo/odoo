# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from unittest.mock import patch
from freezegun import freeze_time

from odoo.addons.account.models.account_move import AccountMove
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import models, fields
from odoo.tests.common import Form, tagged
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT

@tagged('post_install', '-at_install')
class TestStockValuation(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.supplier_location = cls.env.ref('stock.stock_location_suppliers')
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.partner_id = cls.env['res.partner'].create({'name': 'Wood Corner Partner'})
        cls.product1 = cls.env['product.product'].create({'name': 'Large Desk'})

        cls.cat = cls.env['product.category'].create({
            'name': 'cat',
        })
        cls.product1 = cls.env['product.product'].create({
            'name': 'product1',
            'type': 'product',
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
        old_action_post = AccountMove.action_post
        old_create = models.BaseModel.create

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

    def test_fifo_anglosaxon_return_pdiff(self):
        self.env.cr.now = fields.Datetime.now
        self.env.company.anglo_saxon_accounting = True
        self.product1.product_tmpl_id.categ_id.property_cost_method = 'fifo'
        self.product1.product_tmpl_id.categ_id.property_valuation = 'real_time'
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
        receipt_po1.move_ids.quantity_done = 10
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
                    'product_uom': self.product1.uom_po_id.id,
                    'price_unit': 20.0,
                    'date_planned': datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                }),
            ],
        })
        po2.button_confirm()
        receipt_po2 = po2.picking_ids[0]
        receipt_po2.move_ids.quantity_done = 10
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
        with freeze_time(fields.date.today() + timedelta(days=1)):
            stock_return_picking_form = Form(self.env['stock.return.picking']
                .with_context(active_ids=receipt_po2.ids, active_id=receipt_po2.ids[0],
                active_model='stock.picking'))
            stock_return_picking = stock_return_picking_form.save()
            stock_return_picking.product_return_moves.quantity = 10
            stock_return_picking_action = stock_return_picking.create_returns()
            return_pick = self.env['stock.picking'].browse(stock_return_picking_action['res_id'])
            return_pick.move_ids[0].move_line_ids[0].qty_done = 10
            return_pick.button_validate()

            # valuation of product1 should be 200 as the first items will be sent out
            self.assertEqual(self.product1.value_svl, 200)

        with freeze_time(fields.date.today() + timedelta(days=2)):
            # create a credit note for po2
            move_form = Form(self.env['account.move'].with_context(default_move_type='in_refund'))
            move_form.invoice_date = move_form.date
            move_form.partner_id = self.partner_id
            move_form._view['modifiers']['purchase_id']['invisible'] = False
            move_form.purchase_id = po2
            with move_form.invoice_line_ids.edit(0) as line_form:
                line_form.quantity = 10
            creditnote_po2 = move_form.save()
            creditnote_po2.action_post()

        # check the anglo saxon entries
        price_diff_entry = self.env['account.move.line'].search([('account_id', '=', self.price_diff_account.id)])
        self.assertEqual(price_diff_entry.credit, 100)
