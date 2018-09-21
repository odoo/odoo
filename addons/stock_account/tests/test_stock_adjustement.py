# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests import common


class TestAdjustement(common.TransactionCase):

    def setUp(self):
        super(TestAdjustement, self).setUp()
        self.stock_location = self.env.ref('stock.stock_location_stock')


    def test_standard_1(self):

        # Create product
        product_form = Form(self.env['product.product'])
        product_form.name = 'My product 1'
        product_form.type = 'product'
        product_form.standard_price = 20.0
        product_form.categ_id.write({
            'property_cost_method': 'standard',
        })
        finished_product_id = product_form.save()

        # Create inventory
        inventory_form = Form(self.env['stock.inventory'])
        inventory_form.name = 'My Periodic Inventory'
        inventory_form.filter = 'product'
        inventory_form.product_id = finished_product_id
        finished_inventory_id = inventory_form.save()
        finished_inventory_id.action_start()

        with Form(finished_inventory_id) as f:
            with f.line_ids.edit(0) as line:
                line.product_qty = 10
                with self.assertRaises(AssertionError):
                    line.unit_cost = 200

        self.assertEquals(finished_inventory_id.line_ids[0].unit_cost, 20, "unit_cost is not 20")
        finished_inventory_id.action_validate()
        self.assertEquals(finished_inventory_id.move_ids[0].price_unit, 20, "product price in stock move is not 20")
        self.assertEquals(finished_inventory_id.move_ids[0].product_id.stock_value, 200, "stock_value is not 200")
        self.assertEquals(finished_product_id.stock_value, 200, "stock_value is not 200")

    def test_standard_2(self):

        # Create product
        product_form_2 = Form(self.env['product.product'])
        product_form_2.name = 'My product 2'
        product_form_2.type = 'product'
        product_form_2.standard_price = 30.0
        product_form_2.categ_id.write({
            'property_cost_method': 'fifo',
        })
        finished_product_id_2 = product_form_2.save()

        # Create inventory
        inventory_form_2 = Form(self.env['stock.inventory'])
        inventory_form_2.name = 'My Periodic Inventory 2'
        inventory_form_2.filter = 'product'
        inventory_form_2.product_id = finished_product_id_2
        finished_inventory_id_2 = inventory_form_2.save()

        finished_inventory_id_2.action_start()

        with Form(finished_inventory_id_2) as f:
            with f.line_ids.edit(0) as line:
                line.product_qty = 10
                line.unit_cost = 40

        self.assertEquals(finished_inventory_id_2.line_ids[0].unit_cost, 40, "unit_cost is not 40")
        finished_inventory_id_2.action_validate()
        self.assertEquals(finished_inventory_id_2.move_ids[0].product_id.stock_value, 400, "stock_value is not 400")
        self.assertEquals(finished_product_id_2.stock_value, 400, "stock_value is not 400")

        # Create inventory
        inventory_form_3 = Form(self.env['stock.inventory'])
        inventory_form_3.name = 'My Periodic Inventory 3'
        inventory_form_3.filter = 'product'
        inventory_form_3.product_id = finished_product_id_2
        finished_inventory_id_3 = inventory_form_3.save()

        finished_inventory_id_3.action_start()

        with Form(finished_inventory_id_3) as f:
            with f.line_ids.edit(0) as line:
                line.product_qty = 20
                line.unit_cost = 10

        self.assertEquals(finished_inventory_id_3.line_ids[0].unit_cost, 10, "unit_cost is not 10")
        finished_inventory_id_3.action_validate()
        self.assertEquals(finished_inventory_id_3.move_ids[0].product_id.stock_value, 500, "stock_value is not 500")
        self.assertEquals(finished_product_id_2.stock_value, 500, "stock_value is not 500")

    def test_standard_3(self):

        # Create product
        product_form_3 = Form(self.env['product.product'])
        product_form_3.name = 'My product 3'
        product_form_3.type = 'product'
        product_form_3.standard_price = 70.0
        product_form_3.categ_id.write({
            'property_cost_method': 'average',
        })
        finished_product_id_3 = product_form_3.save()

        # Create inventory
        inventory_form_4 = Form(self.env['stock.inventory'])
        inventory_form_4.name = 'My Periodic Inventory 3'
        inventory_form_4.filter = 'product'
        inventory_form_4.product_id = finished_product_id_3
        finished_inventory_id_4 = inventory_form_4.save()

        finished_inventory_id_4.action_start()

        with Form(finished_inventory_id_4) as f:
            with f.line_ids.edit(0) as line:
                line.product_qty = 10
                line.unit_cost = 40

        self.assertEquals(finished_inventory_id_4.line_ids[0].unit_cost, 40, "unit_cost is not 40")
        finished_inventory_id_4.action_validate()
        self.assertEquals(finished_inventory_id_4.move_ids[0].product_id.stock_value, 400, "stock_value is not 400")
        self.assertEquals(finished_product_id_3.stock_value, 400, "stock_value is not 400")


        # Create inventory
        inventory_form_5 = Form(self.env['stock.inventory'])
        inventory_form_5.name = 'My Periodic Inventory 3'
        inventory_form_5.filter = 'product'
        inventory_form_5.product_id = finished_product_id_3
        finished_inventory_id_5 = inventory_form_5.save()

        finished_inventory_id_5.action_start()

        with Form(finished_inventory_id_5) as f:
            with f.line_ids.edit(0) as line:
                line.product_qty = 20
                line.unit_cost = 10

        self.assertEquals(finished_inventory_id_5.line_ids[0].unit_cost, 10, "unit_cost is not 10")
        finished_inventory_id_5.action_validate()
        self.assertEquals(finished_inventory_id_5.move_ids[0].product_id.stock_value, 500, "stock_value is not 500")
        self.assertEquals(finished_product_id_3.stock_value, 500, "stock_value is not 500")
