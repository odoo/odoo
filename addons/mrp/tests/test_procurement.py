# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.exceptions import UserError

class TestProcurement(TestMrpCommon):

    def test_procurement(self):
        """This test case when create production order check procurement is create"""
        # Update BOM
        self.bom_3.bom_line_ids.filtered(lambda x: x.product_id == self.product_5).unlink()
        self.bom_1.bom_line_ids.filtered(lambda x: x.product_id == self.product_1).unlink()

        # Update route
        self.warehouse = self.env.ref('stock.warehouse0')
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        self.product_4.write({'route_ids': [(6, 0, [route_manufacture, route_mto])]})

        # Create production order
        # -------------------------
        # Product6 Unit 24
        #    Product4 8 Dozen
        #    Product2 12 Unit
        # -----------------------

        production_product_6 = self.env['mrp.production'].create({
            'name': 'MO/Test-00002',
            'product_id': self.product_6.id,
            'product_qty': 24,
            'bom_id': self.bom_3.id,
            'product_uom_id': self.product_6.uom_id.id,
        })
        production_product_6.action_assign()

        # check production state is Confirmed
        self.assertEqual(production_product_6.state, 'confirmed', 'Production order should be for Confirmed state')

        # Check procurement for product 4 created or not.
        # Check it created a purchase order

        move_raw_product4 = production_product_6.move_raw_ids.filtered(lambda x: x.product_id == self.product_4)
        produce_product_4 = self.env['mrp.production'].search([('product_id', '=', self.product_4.id),
                                                               ('move_dest_ids', '=', move_raw_product4[0].id)])
        # produce product
        self.assertEqual(produce_product_4.availability, 'waiting', "Consume material not available")

        # Create production order
        # -------------------------
        # Product 4  96 Unit
        #    Product2 48 Unit
        # ---------------------
        # Update Inventory
        inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.product_2.id,
            'new_quantity': 48,
        })
        inventory_wizard.change_product_qty()
        produce_product_4.action_assign()
        self.assertEqual(produce_product_4.product_qty, 8, "Wrong quantity of finish product.")
        self.assertEqual(produce_product_4.product_uom_id, self.uom_dozen, "Wrong quantity of finish product.")
        self.assertEqual(produce_product_4.availability, 'assigned', "Consume material not available")

        # produce product4
        # ---------------

        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': produce_product_4.id,
            'active_ids': [produce_product_4.id],
        }))
        produce_form.product_qty = produce_product_4.product_qty
        product_produce = produce_form.save()
        product_produce.do_produce()
        produce_product_4.post_inventory()
        # Check procurement and Production state for product 4.
        produce_product_4.button_mark_done()
        self.assertEqual(produce_product_4.state, 'done', 'Production order should be in state done')

        # Produce product 6
        # ------------------

        # Update Inventory
        inventory_wizard = self.env['stock.change.product.qty'].create({
            'product_id': self.product_2.id,
            'new_quantity': 12,
        })
        inventory_wizard.change_product_qty()
        production_product_6.action_assign()

        # ------------------------------------

        self.assertEqual(production_product_6.availability, 'assigned', "Consume material not available")
        produce_form = Form(self.env['mrp.product.produce'].with_context({
            'active_id': production_product_6.id,
            'active_ids': [production_product_6.id],
        }))
        produce_form.product_qty = production_product_6.product_qty
        product_produce = produce_form.save()
        product_produce.do_produce()
        production_product_6.post_inventory()
        # Check procurement and Production state for product 6.
        production_product_6.button_mark_done()
        self.assertEqual(production_product_6.state, 'done', 'Production order should be in state done')
        self.assertEqual(self.product_6.qty_available, 24, 'Wrong quantity available of finished product.')

    def test_procurement_2(self):
        """Check that a manufacturing order create the right procurements when the route are set on
        a parent category of a product"""
        # find a child category id
        all_categ_id = self.env['product.category'].search([('parent_id', '=', None)], limit=1)
        child_categ_id = self.env['product.category'].search([('parent_id', '=', all_categ_id.id)], limit=1)

        # set the product of `self.bom_1` to this child category
        for bom_line_id in self.bom_1.bom_line_ids:
            # check that no routes are defined on the product
            self.assertEquals(len(bom_line_id.product_id.route_ids), 0)
            # set the category of the product to a child category
            bom_line_id.product_id.categ_id = child_categ_id

        # set the MTO route to the parent category (all)
        self.warehouse = self.env.ref('stock.warehouse0')
        mto_route = self.warehouse.mto_pull_id.route_id
        mto_route.product_categ_selectable = True
        all_categ_id.write({'route_ids': [(6, 0, [mto_route.id])]})

        # create MO, but check it raises error as components are in make to order and not everyone has 
        with self.assertRaises(UserError):
            production_product_4 = self.env['mrp.production'].create({
                'name': 'MO/Test-00002',
                'product_id': self.product_4.id,
                'product_qty': 1,
                'bom_id': self.bom_1.id,
                'product_uom_id': self.product_4.uom_id.id,
            })