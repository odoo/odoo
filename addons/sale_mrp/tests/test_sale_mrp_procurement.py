# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from datetime import datetime

from odoo.tests.common import TransactionCase


class TestSaleMrpProcurement(TransactionCase):

    def test_sale_mrp(self):
        # In order to test the sale_mrp module in OpenERP, I start by creating a new product 'Slider Mobile'
        # I define product category Mobile Products Sellable.

        product_category_allproductssellable0 = self.env['product.category'].create({
            'name': 'Mobile Products Sellable'
        })

        # I define product category Mobile Services.
        product_category_16 = self.env['product.category'].create({
            'name': 'Mobile Services',
        })

        uom_unit = self.env.ref('product.product_uom_unit')

        # I define product template for Slider Mobile.
        product_template_slidermobile0 = self.env['product.template'].create({
            'categ_id': product_category_allproductssellable0.id,
            'list_price': 200.0,
            'name': 'Slider Mobile',
            'standard_price': 189.0,
            'type': 'product',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        # I define a product Slider Mobile
        product_product_slidermobile0 = self.env['product.product'].create({
            'categ_id': product_category_allproductssellable0.id,
            'list_price': 200.0,
            'name': 'Slider Mobile',
            'seller_ids': [(0, 0, {
                'delay': 1,
                'name': self.env.ref('base.res_partner_2').id,
                'min_qty': 2.0,
            })],
            'standard_price': 189.0,
            'type': 'product',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        # I add the routes manufacture and mto to the product
        product_product_slidermobile0.write({
            'route_ids': [(6, 0, [
                self.env.ref('stock.warehouse0').mto_pull_id.route_id.id,
                self.env.ref('stock.warehouse0').manufacture_pull_id.route_id.id,
            ])]
        })

        # I create a Bill of Material record for Slider Mobile
        mrp_bom_slidermobile0 = self.env['mrp.bom'].create({
            'company_id': self.env.ref('base.main_company').id,
            'product_tmpl_id': product_template_slidermobile0.id,
            'product_id': product_product_slidermobile0.id,
            'product_qty': 1.0,
            'product_uom_id': uom_unit.id,
            'sequence': 0.0,
            'type': 'normal',
        })

        # I create a sale order for product Slider mobile
        sale_order_so0 = self.env['sale.order'].create({
            'client_order_ref': 'ref1',
            'date_order': time.strftime('%Y-%m-%d'),
            'name': 'Test_SO001',
            'order_line': [(0, 0, {
                'name': 'Slider Mobile',
                'price_unit': 200,
                'product_uom': uom_unit.id,
                'product_uom_qty': 500.0,
                'state': 'draft',
                'customer_lead': 7.0,
                'product_id': product_product_slidermobile0.id,
            })],
            'partner_id': self.env.ref('base.res_partner_4').id,
            'partner_invoice_id': self.env.ref('base.res_partner_address_7').id,
            'partner_shipping_id': self.env.ref('base.res_partner_address_7').id,
            'picking_policy': 'direct',
            'pricelist_id': self.env.ref('product.list0').id,
        })

        # I confirm the sale order
        sale_order_so0.action_confirm()

        # I verify that a manufacturing order has been generated, and that its name and reference are correct
        mo = self.env['mrp.production'].search([('origin', 'like', sale_order_so0.name)], limit=1)
        self.assertTrue(mo, 'Manufacturing order has not been generated')
