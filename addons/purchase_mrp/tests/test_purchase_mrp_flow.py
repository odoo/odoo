# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common, Form
from odoo.exceptions import UserError
from odoo import fields

class TestPurchaseMrpFlow(common.TransactionCase):


    def test_01_purchase_mrp_anglo_saxon(self):
        """Test the price unit of a kit"""
        # This test will check that the correct journal entries are created when a consumable product in real time valuation
        # and in fifo cost method is sold in a company using anglo-saxon.
        # For this test, let's consider a product category called Test category in real-time valuation and real price costing method
        # Let's  also consider a finished product with a bom with two components: component1(cost = 20) and component2(cost = 10)
        # These products are in the Test category
        # The bom consists of 2 component1 and 1 component2
        # The invoice policy of the finished product is based on ordered quantities
        self.categ_unit = self.env.ref('uom.product_uom_categ_unit')
        self.uom_unit = self.uom_unit = self.env['uom.uom'].search([('category_id', '=', self.categ_unit.id), ('uom_type', '=', 'reference')], limit=1)
        self.company = self.env.ref('base.main_company')
        self.company.anglo_saxon_accounting = True
        self.partner = self.env.ref('base.res_partner_1')
        self.category = self.env.ref('product.product_category_1').copy({'name': 'Test category','property_valuation': 'real_time', 'property_cost_method': 'fifo'})
        account_type = self.env['account.account.type'].create({'name': 'RCV type', 'type': 'receivable'})
        self.account_receiv = self.env['account.account'].create({'name': 'Receivable', 'code': 'RCV00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.account_input = self.env['account.account'].create({'name': 'Input', 'code': 'INP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_expense = self.env['account.account'].create({'name': 'Expense', 'code': 'EXP00' , 'user_type_id': account_type.id, 'reconcile': True})
        account_output = self.env['account.account'].create({'name': 'Output', 'code': 'OUT00' , 'user_type_id': account_type.id, 'reconcile': True})
        self.partner.property_account_receivable_id = self.account_receiv
        self.category.property_account_income_categ_id = self.account_receiv
        self.category.property_account_expense_categ_id = account_expense
        self.category.property_stock_account_input_categ_id = self.account_input
        self.category.property_stock_account_output_categ_id = account_output
        self.category.property_stock_valuation_account_id = self.account_receiv
        self.category.property_stock_journal = self.env['account.journal'].create({'name': 'Stock journal', 'type': 'purchase', 'code': 'STK00'})

        Product = self.env['product.product']
        self.finished_product = Product.create({
                'name': 'Finished product',
                'type': 'consu',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'purchase_method': 'purchase',
                'supplier_taxes_id': [(6, 0, [])]})
        self.component1 = Product.create({
                'name': 'Component 1',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'supplier_taxes_id': [(6, 0, [])],
                'purchase_method': 'purchase',
                'standard_price': 20})
        self.component2 = Product.create({
                'name': 'Component 2',
                'type': 'product',
                'uom_id': self.uom_unit.id,
                'categ_id': self.category.id,
                'supplier_taxes_id': [(6, 0, [])],
                'purchase_method': 'purchase',
                'standard_price': 10})
        self.bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.finished_product.product_tmpl_id.id,
                'product_qty': 1.0,
                'type': 'phantom'})
        BomLine = self.env['mrp.bom.line']
        BomLine.create({
                'product_id': self.component1.id,
                'product_qty': 2.0,
                'bom_id': self.bom.id})
        BomLine.create({
                'product_id': self.component2.id,
                'product_qty': 1.0,
                'bom_id': self.bom.id})
        # Create a PO for a specific partner for three units of the finished product
        po_vals = {
            'partner_id': self.partner.id,
            'order_line': [(0, 0, {'name': self.finished_product.name, 'product_id': self.finished_product.id, 'product_qty': 3, 'product_uom': self.finished_product.uom_id.id, 'price_unit': 60.0, 'date_planned': fields.Datetime.now()})],
            'company_id': self.company.id,
            'currency_id': self.company.currency_id.id,
        }
        self.po = self.env['purchase.order'].create(po_vals)
        # Validate the PO
        self.po.button_confirm()
        self.invoice = self.env['account.invoice'].create({
            'partner_id': self.partner.id,
            'purchase_id': self.po.id,
            'account_id': self.account_receiv.id,
            'type': 'in_invoice'
        })
        self.invoice.purchase_order_change()
        self.invoice.action_invoice_open()
        aml = self.invoice.move_id.line_ids
        aml_input = aml.filtered(lambda l: l.account_id.id == self.account_input.id)
        self.assertEqual(aml_input.debit, 180, "Cost of Good Sold entry missing or mismatching")
