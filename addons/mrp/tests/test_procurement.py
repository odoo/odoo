# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mrp.tests.common import TestMrpCommon


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
        procurement = self.env['procurement.order'].search([('group_id', '=', production_product_6.procurement_group_id.id), ('product_id', '=', self.product_4.id)])
        self.assertTrue(procurement, 'No procurement are created !')
        self.assertEqual(procurement.state, 'running', 'Procurement order should be in state running')

        produce_product_4 = procurement.production_id
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

        produce_wizard = self.env['mrp.product.produce'].with_context({
            'active_id': produce_product_4.id,
            'active_ids': [produce_product_4.id],
        }).create({
            'product_qty': produce_product_4.product_qty,
        })
        produce_wizard.do_produce()
        produce_product_4.post_inventory()
        # Check procurement and Production state for product 4.
        produce_product_4.button_mark_done()
        self.assertEqual(produce_product_4.state, 'done', 'Production order should be in state done')
        self.assertEqual(procurement.state, 'done', 'Procurement order should be in state done')

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
        produce_wizard = self.env['mrp.product.produce'].with_context({
            'active_id': production_product_6.id,
            'active_ids': [production_product_6.id],
        }).create({
            'product_qty': production_product_6.product_qty,
        })
        produce_wizard.do_produce()

        production_product_6.post_inventory()
        # Check procurement and Production state for product 6.
        production_product_6.button_mark_done()
        self.assertEqual(production_product_6.state, 'done', 'Production order should be in state done')
        self.assertEqual(self.product_6.qty_available, 24, 'Wrong quantity available of finished product.')
