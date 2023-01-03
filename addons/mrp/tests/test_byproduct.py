# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests import common


class TestMrpByProduct(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.MrpBom = cls.env['mrp.bom']
        cls.warehouse = cls.env.ref('stock.warehouse0')
        route_manufacture = cls.warehouse.manufacture_pull_id.route_id.id
        route_mto = cls.warehouse.mto_pull_id.route_id.id
        cls.uom_unit_id = cls.env.ref('uom.product_uom_unit').id
        def create_product(name, route_ids=[]):
            return cls.env['product.product'].create({
                'name': name,
                'type': 'product',
                'route_ids': route_ids})

        # Create product A, B, C.
        # --------------------------
        cls.product_a = create_product('Product A', route_ids=[(6, 0, [route_manufacture, route_mto])])
        cls.product_b = create_product('Product B', route_ids=[(6, 0, [route_manufacture, route_mto])])
        cls.product_c_id = create_product('Product C', route_ids=[]).id

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
            'byproduct_ids': [(0, 0, {'product_id': self.product_b.id, 'product_uom_id': self.uom_unit_id, 'product_qty': 1})]
            })

        # Create production order for product A
        # -------------------------------------

        mnf_product_a_form = Form(self.env['mrp.production'])
        mnf_product_a_form.product_id = self.product_a
        mnf_product_a_form.bom_id = bom_product_a
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

    def test_default_uom(self):
        """ Tests the `uom_id` on the byproduct gets set automatically while creating a byproduct with a product,
            without the need to call an onchange or to set the uom manually in the create.
        """
        # Set a specific UOM on the byproduct on purpose to make sure it's not just a default on the unit UOM
        # that makes the test pass.
        self.product_b.product_tmpl_id.uom_id = self.env.ref('uom.product_uom_dozen')
        bom = self.MrpBom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'byproduct_ids': [(0, 0, {'product_id': self.product_b.id, 'product_qty': 1})]
        })
        self.assertEqual(bom.byproduct_ids.product_uom_id, self.env.ref('uom.product_uom_dozen'))

    def test_finished_and_byproduct_moves(self):
        """
            Tests the behavior of the `create` override in the model `mrp.production`
            regarding the values for the fields `move_finished_ids` and `move_byproduct_ids`.
            The behavior is a bit tricky, because the moves included in `move_byproduct_ids`
            are included in the `move_finished_ids`. `move_byproduct_ids` is a subset of `move_finished_ids`.

            So, when creating a manufacturing order, whether:
            - Only `move_finished_ids` is passed, containing both the finished product and the by-products of the BOM,
            - Only `move_byproduct_ids` is passed, only containing the by-products of the BOM,
            - Both `move_finished_ids` and `move_byproduct_ids` are passed,
              holding the product finished and the byproducts respectively
            At the end, in the created manufacturing order
            `move_finished_ids` must contain both the finished product, and the by-products,
            `move_byproduct_ids` must contain only the by-products.

            Besides, the code shouldn't raise an error
            because only one of the two `move_finished_ids`, `move_byproduct_ids` is provided.

            In addition, the test voluntary sets a different produced quantity
            for the finished product and the by-products moves than defined in the BOM
            as it's the point to manually pass the `move_finished_ids` and `move_byproduct_ids`
            when creating a manufacturing order, set different values than the defaults, in this case
            a different produced quantity than the defaults from the BOM.
        """
        bom_product_a = self.MrpBom.create({
            'product_tmpl_id': self.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                'product_id': self.product_c_id, 'product_uom_id': self.uom_unit_id, 'product_qty': 2.0
            })],
            'byproduct_ids': [(0, 0, {
                'product_id': self.product_b.id, 'product_uom_id': self.uom_unit_id, 'product_qty': 1.0
            })]
        })
        for expected_finished_qty, expected_byproduct_qty, values in [
            # Only `move_finished_ids` passed, containing both the finished product and the by-product
            (3.0, 4.0, {
                'move_finished_ids': [
                    (0, 0, {
                        'product_id': self.product_a.id,
                        'product_uom_qty': 3.0,
                        'location_id': self.product_a.property_stock_production,
                        'location_dest_id': self.warehouse.lot_stock_id.id,
                    }),
                    (0, 0, {
                        'product_id': self.product_b.id,
                        'product_uom_qty': 4.0,
                        'location_id': self.product_a.property_stock_production,
                        'location_dest_id': self.warehouse.lot_stock_id.id,
                    }),
                ],
            }),
            # Only `move_byproduct_ids` passed, containing the by-product move only
            (2.0, 4.0, {
                'move_byproduct_ids': [
                    (0, 0, {
                        'product_id': self.product_b.id,
                        'product_uom_qty': 4.0,
                        'location_id': self.product_a.property_stock_production,
                        'location_dest_id': self.warehouse.lot_stock_id.id,
                    }),
                ],
            }),
            # Both `move_finished_ids` and `move_byproduct_ids` passed,
            # containing respectively the finished product and the by-product
            (3.0, 4.0, {
                'move_finished_ids': [
                    (0, 0, {
                        'product_id': self.product_a.id,
                        'product_uom_qty': 3.0,
                        'location_id': self.product_a.property_stock_production,
                        'location_dest_id': self.warehouse.lot_stock_id.id,
                    }),
                ],
                'move_byproduct_ids': [
                    (0, 0, {
                        'product_id': self.product_b.id,
                        'product_uom_qty': 4.0,
                        'location_id': self.product_a.property_stock_production,
                        'location_dest_id': self.warehouse.lot_stock_id.id,
                    }),
                ],
            }),
        ]:
            mo = self.env['mrp.production'].create({
                'product_id': self.product_a.id,
                'bom_id': bom_product_a.id,
                'product_qty': 2.0,
                **values,
            })
            self.assertEqual(mo.move_finished_ids.product_id, self.product_a + self.product_b)
            self.assertEqual(mo.move_byproduct_ids.product_id, self.product_b)

            finished_move = mo.move_finished_ids.filtered(lambda x: x.product_id == self.product_a)
            self.assertEqual(
                finished_move.product_uom_qty, expected_finished_qty, "Wrong produced quantity of finished product."
            )

            by_product_move = mo.move_finished_ids.filtered(lambda x: x.product_id == self.product_b)
            self.assertEqual(
                by_product_move.product_uom_qty, expected_byproduct_qty, "Wrong produced quantity of by-product."
            )

            # Also check the produced quantity of the by-product through `move_byproduct_ids`
            self.assertEqual(
                mo.move_byproduct_ids.product_uom_qty, expected_byproduct_qty, "Wrong produced quantity of by-product."
            )
