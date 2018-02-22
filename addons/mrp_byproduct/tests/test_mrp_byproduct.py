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

        # Create BOM for product A and set byproduct product B
        bom_product_a = self.MrpBom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': self.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': self.product_c_id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2})],
            'sub_products': [(0, 0, {'product_id': self.product_b.id, 'product_uom_id': self.uom_unit_id, 'product_qty': 1})]
            })

        # Create production order for product A
        # -------------------------------------

        mnf_product_a = self.env['mrp.production'].create({
                        'product_id': self.product_a.id,
                        'product_qty': 2.0,
                        'product_uom_id': self.uom_unit_id,
                        'bom_id': bom_product_a.id,
                    })

        # I compute the data of production order
        context = {"active_model": "mrp.production", "active_ids": [mnf_product_a.id], "active_id": mnf_product_a.id}

        # I confirm the production order.
        self.assertEqual(mnf_product_a.state, 'confirmed', 'Production order should be in state confirmed')

        # Now I check the stock moves for the byproduct I created in the bill of material.
        # This move is created automatically when I confirmed the production order.
        moves = mnf_product_a.move_raw_ids | mnf_product_a.move_finished_ids
        self.assertTrue(moves, 'No moves are created !')

        # I consume and produce the production of products.
        # I create record for selecting mode and quantity of products to produce.
        produce_form = Form(self.env['mrp.product.produce'].with_context(context))
        produce_form.product_qty = 2.00
        product_consume = produce_form.save()
        # I finish the production order.
        self.assertEqual(len(mnf_product_a.move_raw_ids), 1, "Wrong consume move on production order.")
        product_consume.do_produce()
        consume_move_c = mnf_product_a.move_raw_ids
        by_product_move = mnf_product_a.move_finished_ids.filtered(lambda x: x.product_id.id == self.product_b.id)
        # Check sub production produced quantity...
        self.assertEqual(consume_move_c.product_uom_qty, 4, "Wrong consumed quantity of product c.")
        self.assertEqual(by_product_move.product_uom_qty, 2, "Wrong produced quantity of sub product.")

        mnf_product_a.post_inventory()

        # I see that stock moves of External Hard Disk including Headset USB are done now.
        self.assertFalse(any(move.state != 'done' for move in moves), 'Moves are not done!')
