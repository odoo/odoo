# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon
from odoo.tests import tagged

import time


@tagged('-at_install', 'post_install')
class TestAveragePrice(ValuationReconciliationTestCommon):

    def test_00_average_price(self):
        """ Testcase for average price computation"""

        res_partner_3 = self.env['res.partner'].create({
            'name': 'Gemini Partner',
        })

        # Set a product as using average price.
        product_cable_management_box = self.env['product.product'].create({
            'default_code': 'AVG',
            'name': 'Average Ice Cream',
            'is_storable': True,
            'categ_id': self.stock_account_product_categ.id,
            'list_price': 100.0,
            'standard_price': 60.0,
            'uom_id': self.env.ref('uom.product_uom_kgm').id,
            'supplier_taxes_id': [],
            'description': 'FIFO Ice Cream',
        })
        product_cable_management_box.categ_id.property_cost_method = 'average'

        # I create a draft Purchase Order for first incoming shipment for 10 pieces at 60€
        purchase_order_1 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
            'order_line': [(0, 0, {
                'name': 'Average Ice Cream',
                'product_id': product_cable_management_box.id,
                'product_qty': 10.0,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 60.0,
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # Confirm the first purchase order
        purchase_order_1.button_confirm()

        # Check the "Approved" status of purchase order 1
        self.assertEqual(purchase_order_1.state, 'purchase', "Wrong state of purchase order!")

        # Process the reception of purchase order 1
        picking = purchase_order_1.picking_ids[0]
        picking.button_validate()

        # Check the average_price of the product (average icecream).
        self.assertEqual(product_cable_management_box.qty_available, 10.0, 'Wrong quantity in stock after first reception')
        self.assertEqual(product_cable_management_box.standard_price, 60.0, 'Standard price should be the price of the first reception!')

        # I create a draft Purchase Order for second incoming shipment for 30 pieces at 80€
        purchase_order_2 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
            'order_line': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_qty': 30.0,
                'product_uom_id': self.env.ref('uom.product_uom_kgm').id,
                'price_unit': 80.0,
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # Confirm the second purchase order
        purchase_order_2.button_confirm()
        # Process the reception of purchase order 2
        picking = purchase_order_2.picking_ids[0]
        picking.button_validate()

        # Check the standard price
        self.assertEqual(product_cable_management_box.standard_price, 75.0, 'After second reception, we should have an average price of 75.0 on the product')

        # Create picking to send some goods
        outgoing_shipment = self.env['stock.picking'].create({
            'picking_type_id': self.company_data['default_warehouse'].out_type_id.id,
            'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'move_ids': [(0, 0, {
                'name': 'outgoing_shipment_avg_move',
                'product_id': product_cable_management_box.id,
                'product_uom_qty': 20.0,
                'product_uom': self.env.ref('uom.product_uom_kgm').id,
                'location_id':  self.company_data['default_warehouse'].lot_stock_id.id,
                'location_dest_id': self.env.ref('stock.stock_location_customers').id})]
            })

        # Assign this outgoing shipment and process the delivery
        outgoing_shipment.action_assign()
        outgoing_shipment.button_validate()

        # Check the average price (60 * 10 + 30 * 80) / 40 = 75.0€ did not change
        self.assertEqual(product_cable_management_box.standard_price, 75.0, 'Average price should not have changed with outgoing picking!')
        self.assertEqual(product_cable_management_box.qty_available, 20.0, 'Pieces were not picked correctly as the quantity on hand is wrong')

        # Make a new purchase order with 500 g Average Ice Cream at a price of 0.2€/g
        purchase_order_3 = self.env['purchase.order'].create({
            'partner_id': res_partner_3.id,
            'order_line': [(0, 0, {
                'name': product_cable_management_box.name,
                'product_id': product_cable_management_box.id,
                'product_qty': 500.0,
                'product_uom_id': self.ref('uom.product_uom_gram'),
                'price_unit': 0.2,
                'date_planned': time.strftime('%Y-%m-%d'),
            })]
        })

        # Confirm the first purchase order
        purchase_order_3.button_confirm()
        # Process the reception of purchase order 3 in grams

        picking = purchase_order_3.picking_ids[0]
        picking.button_validate()

        # Check price is (75.0 * 20 + 200*0.5) / 20.5 = 78.04878€
        self.assertEqual(product_cable_management_box.qty_available, 20.5, 'Reception of purchase order in grams leads to wrong quantity in stock')
        self.assertEqual(round(product_cable_management_box.standard_price, 2), 78.05,
            'Standard price as average price of third reception with other UoM incorrect! Got %s instead of 78.05' % (round(product_cable_management_box.standard_price, 2)))

    def test_inventory_user_svl_access(self):
        """ Test to check if Inventory/User is able to validate a
        transfer when the product has been invoiced already """

        avco_product = self.env['product.product'].create({
            'name': 'Average Ice Cream',
            'is_storable': True,
            'categ_id': self.stock_account_product_categ.id,
            'purchase_method': 'purchase',
        })
        avco_product.categ_id.property_cost_method = 'average'

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': avco_product.id,
                'product_qty': 1.0,
            })]
        })

        purchase_order.button_confirm()
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids[0]

        bill.invoice_date = time.strftime('%Y-%m-%d')
        bill.invoice_line_ids[0].quantity = 1.0
        bill.action_post()

        self.assertEqual(purchase_order.order_line[0].qty_invoiced, 1.0, 'QTY invoiced should have been set to 1 on the purchase order line')

        picking = purchase_order.picking_ids[0]
        picking.move_ids.picked = True
        # clear cash to ensure access rights verification
        self.env.invalidate_all()
        picking.with_user(self.res_users_stock_user).button_validate()

        self.assertEqual(picking.state, 'done', 'Transfer should be in the DONE state')

    def test_bill_before_reciept(self):
        """ Check unit price of recieved product that has been invoiced already """

        avco_product = self.env['product.product'].create({
            'name': 'Average Ice Cream',
            'is_storable': True,
            'categ_id': self.stock_account_product_categ.id,
            'purchase_method': 'purchase',
        })
        avco_product.categ_id.property_cost_method = 'average'

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': avco_product.id,
                'product_qty': 1.0,
            })]
        })

        purchase_order.button_confirm()
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids[0]

        bill.invoice_date = time.strftime('%Y-%m-%d')
        bill.invoice_line_ids[0].price_unit = 100.0
        bill.button_cancel()

        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids[1]

        bill.invoice_date = time.strftime('%Y-%m-%d')
        bill.invoice_line_ids[0].price_unit = 300.0
        bill.invoice_line_ids[0].quantity = 1.0
        bill.action_post()

        picking = purchase_order.picking_ids[0]
        picking.button_validate()

        self.assertEqual(avco_product.avg_cost, 300)

    def test_svl_avco_with_discount(self):
        """
            Ensure the stock valuation is correct when
            the purchase order has a discount and the
            product was invoiced before being received
        """

        avco_product = self.env['product.product'].create({
            'name': 'Average Ice Cream',
            'type': 'consu',
            'categ_id': self.stock_account_product_categ.id,
            'purchase_method': 'purchase',
        })
        avco_product.categ_id.property_cost_method = 'average'

        purchase_order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': avco_product.id,
                'product_qty': 10.0,
                'price_unit': 10.0,
                'discount': 10.0,
            })]
        })

        purchase_order.button_confirm()
        purchase_order.action_create_invoice()
        bill = purchase_order.invoice_ids[0]

        bill.invoice_date = time.strftime('%Y-%m-%d')
        bill.action_post()

        picking = purchase_order.picking_ids[0]
        picking.button_validate()

        self.assertEqual(avco_product.avg_cost, 9)
        self.assertEqual(avco_product.value_svl, 90)

    def test_no_compensatory_svl_from_asymmetrical_rounding(self):
        """ Ensure that a purchase order for a high quantity of some product using avg costing does
        not calculate the price unit asymmetrically for the order(line) and the invoice AML.
        """
        self.stock_account_product_categ.property_cost_method = 'average'
        avco_product = self.env['product.product'].create({
            'name': 'test_rounding_in_valuation product',
            'is_storable': True,
            'categ_id': self.stock_account_product_categ.id,
            'purchase_method': 'purchase',
            'standard_price': 2.0,
        })

        incl_tax = self.env['account.tax'].create({
            'name': 'test_rounding_in_valuation tax',
            'type_tax_use': 'purchase',
            'amount_type': 'percent',
            'amount': 10,
            'price_include_override': 'tax_included',
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {
                    'repartition_type': 'tax',
                    'factor_percent': 100,
                    'account_id': self.env['account.account'].search([('name', '=', 'Tax Paid')], limit=1).id,
                }),
            ],
            'include_base_amount': False,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [(0, 0, {
                'product_id': avco_product.id,
                'product_qty': 999,
                'taxes_id': [(6, 0, [incl_tax.id])],
            })],
        })
        po.button_confirm()

        po.picking_ids.move_ids.quantity = 999
        po.picking_ids.button_validate()
        po.action_create_invoice()
        po.invoice_ids[0].invoice_date = time.strftime('%Y-%m-%d')
        po.invoice_ids[0].action_post()

        self.assertFalse(po.picking_ids.move_ids.stock_valuation_layer_ids.stock_valuation_layer_ids)
