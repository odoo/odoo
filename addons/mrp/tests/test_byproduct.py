# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests import common


class TestMrpByProduct(common.TransactionCase):

    def setUp(self):
        super(TestMrpByProduct, self).setUp()
        self.MrpBom = self.env['mrp.bom']
        self.warehouse = self.env.ref('stock.warehouse0')
        route_manufacture = self.warehouse.manufacture_pull_id.route_id.id
        route_mto = self.warehouse.mto_pull_id.route_id.id
        self.uom_unit_id = self.ref('uom.product_uom_unit')
        def create_product(name, route_ids=[]):
            return self.env['product.product'].create({
                'name': name,
                'type': 'product',
                'route_ids': route_ids})

        # Create product A, B, C.
        # --------------------------
        self.product_a = create_product('Product A', route_ids=[(6, 0, [route_manufacture, route_mto])])
        self.product_b = create_product('Product B', route_ids=[(6, 0, [route_manufacture, route_mto])])
        self.product_c_id = create_product('Product C', route_ids=[]).id
        self.bom_byproduct = self.MrpBom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': self.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': self.product_c_id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2})],
            'byproduct_ids': [(0, 0, {'product_id': self.product_b.id, 'product_uom_id': self.uom_unit_id, 'product_qty': 1})]
            })

    def test_00_mrp_byproduct(self):
        """ Test by product with production order."""
        # Create BOM for product B
        # ------------------------
        bom_product_b = self.MrpBom.create({
            'product_tmpl_id': self.product_b.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': self.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': self.product_c_id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2})]
            })

        # Create production order for product A
        # -------------------------------------

        mnf_product_a_form = Form(self.env['mrp.production'])
        mnf_product_a_form.product_id = self.product_a
        mnf_product_a_form.bom_id = self.bom_byproduct
        mnf_product_a_form.product_qty = 2.0
        mnf_product_a = mnf_product_a_form.save()
        mnf_product_a.action_confirm()

        # I confirm the production order.
        self.assertEqual(mnf_product_a.state, 'confirmed', 'Production order should be in state confirmed')

        # Now I check the stock moves for the byproduct I created in the bill of material.
        # This move is created automatically when I confirmed the production order.
        moves = mnf_product_a.move_raw_ids | mnf_product_a.move_finished_ids
        self.assertTrue(moves, 'No moves are created !')

        # I consume and produce the production of products.
        # I create record for selecting mode and quantity of products to produce.
        mo_form = Form(mnf_product_a)
        mnf_product_a.move_byproduct_ids.quantity_done = 2
        mo_form.qty_producing = 2.00
        mnf_product_a = mo_form.save()
        # I finish the production order.
        self.assertEqual(len(mnf_product_a.move_raw_ids), 1, "Wrong consume move on production order.")
        consume_move_c = mnf_product_a.move_raw_ids
        by_product_move = mnf_product_a.move_finished_ids.filtered(lambda x: x.product_id.id == self.product_b.id)
        # Check sub production produced quantity...
        self.assertEqual(consume_move_c.product_uom_qty, 4, "Wrong consumed quantity of product c.")
        self.assertEqual(by_product_move.product_uom_qty, 2, "Wrong produced quantity of sub product.")

        mnf_product_a._post_inventory()

        # I see that stock moves of External Hard Disk including Headset USB are done now.
        self.assertFalse(any(move.state != 'done' for move in moves), 'Moves are not done!')

    def test_01_mrp_byproduct(self):
        self.env["stock.quant"].create({
            "product_id": self.product_c_id,
            "location_id": self.warehouse.lot_stock_id.id,
            "quantity": 4,
        })
        bom_product_a = self.MrpBom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': self.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': self.product_c_id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2})]
            })
        mnf_product_a_form = Form(self.env['mrp.production'])
        mnf_product_a_form.product_id = self.product_a
        mnf_product_a_form.bom_id = bom_product_a
        mnf_product_a_form.product_qty = 2.0
        mnf_product_a = mnf_product_a_form.save()
        mnf_product_a.action_confirm()
        self.assertEqual(mnf_product_a.state, "confirmed")
        mnf_product_a.move_raw_ids._action_assign()
        mnf_product_a.move_raw_ids.quantity_done = mnf_product_a.move_raw_ids.product_uom_qty
        mnf_product_a.move_raw_ids._action_done()
        self.assertEqual(mnf_product_a.state, "progress")
        mnf_product_a.qty_producing = 2
        mnf_product_a.button_mark_done()
        self.assertTrue(mnf_product_a.move_finished_ids)
        self.assertEqual(mnf_product_a.state, "done")

    def test_change_product(self):
        """ Create a production order for a specific product with a BoM. Then change the BoM and the finished product for
        other ones and check the finished product of the first mo did not became a byproduct of the second one."""
        # Create BOM for product A with product B as component
        bom_product_a = self.MrpBom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': self.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': self.product_b.id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2})],
            })

        bom_product_a_2 = self.MrpBom.create({
            'product_tmpl_id': self.product_b.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': self.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': self.product_c_id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2})],
            })
        # Create production order for product A
        # -------------------------------------

        mnf_product_a_form = Form(self.env['mrp.production'])
        mnf_product_a_form.product_id = self.product_a
        mnf_product_a_form.bom_id = bom_product_a
        mnf_product_a_form.product_qty = 1.0
        mnf_product_a = mnf_product_a_form.save()
        mnf_product_a_form = Form(mnf_product_a)
        mnf_product_a_form.bom_id = bom_product_a_2
        mnf_product_a = mnf_product_a_form.save()
        self.assertEqual(mnf_product_a.move_raw_ids.product_id.id, self.product_c_id)
        self.assertFalse(mnf_product_a.move_byproduct_ids)

    def test_byproduct_putaway(self):
        """
        Test the byproducts are dispatched correctly with putaway rules. We have
        a byproduct P and two sublocations L01, L02 with a capacity constraint:
        max 2 x P by location. There is already 1 x P at L01. Process a MO with
        2 x P as byproducts. They should be redirected to L02
        """

        self.stock_location = self.env.ref('stock.stock_location_stock')
        stor_category = self.env['stock.storage.category'].create({
            'name': 'Super Storage Category',
            'max_weight': 1000,
            'product_capacity_ids': [(0, 0, {
                'product_id': self.product_b.id,
                'quantity': 2,
            })]
        })
        shelf1_location = self.env['stock.location'].create({
            'name': 'shelf1',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': stor_category.id,
        })
        shelf2_location = self.env['stock.location'].create({
            'name': 'shelf2',
            'usage': 'internal',
            'location_id': self.stock_location.id,
            'storage_category_id': stor_category.id,
        })
        self.env['stock.putaway.rule'].create({
            'product_id': self.product_b.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': self.stock_location.id,
            'storage_category_id': stor_category.id,
        })
        self.env['stock.putaway.rule'].create({
            'product_id': self.product_a.id,
            'location_in_id': self.stock_location.id,
            'location_out_id': shelf2_location.id,
        })

        self.env['stock.quant']._update_available_quantity(self.product_b, shelf1_location, 1)

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_a
        mo_form.bom_id = self.bom_byproduct
        mo_form.product_qty = 2.0
        mo = mo_form.save()
        mo.action_confirm()
        mo_form = Form(mo)
        with mo_form.move_byproduct_ids.edit(0) as move:
            move.quantity_done = 2
        mo_form.qty_producing = 2.00
        mo = mo_form.save()

        mo._post_inventory()
        byproduct_move_line = mo.move_byproduct_ids.move_line_ids
        finished_move_line = mo.move_finished_ids.filtered(lambda m: m.product_id == self.product_a).move_line_ids
        self.assertEqual(byproduct_move_line.location_dest_id, shelf2_location)
        self.assertEqual(finished_move_line.location_dest_id, shelf2_location)
