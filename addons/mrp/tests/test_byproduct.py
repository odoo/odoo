# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form
from odoo.tests import common
from odoo.exceptions import ValidationError


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
        cls.bom_byproduct = cls.MrpBom.create({
            'product_tmpl_id': cls.product_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'product_uom_id': cls.uom_unit_id,
            'bom_line_ids': [(0, 0, {'product_id': cls.product_c_id, 'product_uom_id': cls.uom_unit_id, 'product_qty': 2})],
            'byproduct_ids': [(0, 0, {'product_id': cls.product_b.id, 'product_uom_id': cls.uom_unit_id, 'product_qty': 1})]
            })
        cls.produced_serial = cls.env['product.product'].create({
            'name': 'Produced Serial',
            'type': 'product',
            'tracking': 'serial',
        })
        cls.sn_1 = cls.env['stock.lot'].create({
            'name': 'Serial_01',
            'product_id': cls.produced_serial.id
        })
        cls.sn_2 = cls.env['stock.lot'].create({
            'name': 'Serial_02',
            'product_id': cls.produced_serial.id
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
        mnf_product_a.move_raw_ids.picked = True
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
        mo_form.qty_producing = 2.00
        mo = mo_form.save()

        mo._post_inventory()
        byproduct_move_line = mo.move_byproduct_ids.move_line_ids
        finished_move_line = mo.move_finished_ids.filtered(lambda m: m.product_id == self.product_a).move_line_ids
        self.assertEqual(byproduct_move_line.location_dest_id, shelf2_location)
        self.assertEqual(finished_move_line.location_dest_id, shelf2_location)

    def test_check_byproducts_cost_share(self):
        """
        Test that byproducts with total cost_share > 100% or a cost_share < 0%
        will throw a ValidationError
        """
        # Create new MO
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_a
        mo_form.product_qty = 2.0
        mo = mo_form.save()

        # Create product
        self.product_d = self.env['product.product'].create({
                'name': 'Product D',
                'type': 'product'})
        self.product_e = self.env['product.product'].create({
                'name': 'Product E',
                'type': 'product'})

        # Create byproduct
        byproduct_1 = self.env['stock.move'].create({
            'name': 'By Product 1',
            'product_id': self.product_d.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'production_id': mo.id,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            })
        byproduct_2 = self.env['stock.move'].create({
            'name': 'By Product 2',
            'product_id': self.product_e.id,
            'product_uom': self.ref('uom.product_uom_unit'),
            'production_id': mo.id,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_output'),
            })

        # Update byproduct has cost share > 100%
        with self.assertRaises(ValidationError), self.cr.savepoint():
            byproduct_1.cost_share = 120
            mo.write({'move_byproduct_ids': [(4, byproduct_1.id)]})

        # Update byproduct has cost share < 0%
        with self.assertRaises(ValidationError), self.cr.savepoint():
            byproduct_1.cost_share = -10
            mo.write({'move_byproduct_ids': [(4, byproduct_1.id)]})

        # Update byproducts have total cost share > 100%
        with self.assertRaises(ValidationError), self.cr.savepoint():
            byproduct_1.cost_share = 60
            byproduct_2.cost_share = 70
            mo.write({'move_byproduct_ids': [(6, 0, [byproduct_1.id, byproduct_2.id])]})

    def test_check_byproducts_cost_share_02(self):
        """
        Test that byproducts with total cost_share < 100% with a cancelled moves will don't throw a ValidationError
        """
        self.bom_byproduct.byproduct_ids[0].cost_share = 70
        self.bom_byproduct.byproduct_ids[0].product_qty = 2
        mo = self.env["mrp.production"].create({
            'product_id': self.product_a.id,
            'product_qty': 1.0,
            'bom_id': self.bom_byproduct.id,
        })
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        mo_form = Form(mo)
        mo_form.qty_producing = 1
        mo = mo_form.save()
        self.assertEqual(mo.state, 'to_close')
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_01_check_byproducts_update(self):
        """
        Test that check byproducts update in stock move should also reflect in stock move line(Product moves).
        """
        # Create new MO
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_a
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()

        mo.move_byproduct_ids.write({'product_id': self.product_c_id})
        mo.button_mark_done()
        self.assertEqual(mo.move_byproduct_ids.product_id, mo.move_byproduct_ids.move_line_ids.product_id)

    def test_02_check_byproducts_update(self):
        """
        Case 2: Update Product From Tracked Product to Non Tracked Product.
        """
        self.bom_byproduct.byproduct_ids[0].product_id = self.produced_serial.id
        self.bom_byproduct.byproduct_ids[0].product_qty = 2
        mo = self.env["mrp.production"].create({
            'product_id': self.product_a.id,
            'product_qty': 1.0,
            'bom_id': self.bom_byproduct.id,
        })
        mo.action_confirm()

        mo.move_byproduct_ids.lot_ids = [(4, self.sn_1.id)]
        mo.move_byproduct_ids.lot_ids = [(4, self.sn_2.id)]

        self.assertEqual(len(mo.move_byproduct_ids.move_line_ids), 2)

        mo.move_byproduct_ids.write({'product_id': self.product_c_id})

        mo.button_mark_done()
        self.assertEqual(len(mo.move_byproduct_ids.move_line_ids), 1)
        self.assertEqual(mo.move_byproduct_ids.product_id, mo.move_byproduct_ids.move_line_ids.product_id)

    def test_03_check_byproducts_update(self):
        """
        Case 3: Update Product From Non Tracked Product to Tracked Product.
        """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_a
        mo_form.product_qty = 2.0
        mo = mo_form.save()
        mo.action_confirm()

        mo.move_byproduct_ids.write({'product_id': self.produced_serial.id})

        mo.move_byproduct_ids.lot_ids = [(4, self.sn_1.id)]
        mo.move_byproduct_ids.lot_ids = [(4, self.sn_2.id)]

        mo.button_mark_done()
        self.assertEqual(len(mo.move_byproduct_ids.move_line_ids), 2)
        self.assertEqual(mo.move_byproduct_ids.product_id, mo.move_byproduct_ids.move_line_ids.product_id)

    def test_byproduct_qty_update(self):
        """
        Test that byproduct quantity is updated to the quantity set on the Mo when the Mo is marked as done.ee
        """
        self.bom_byproduct.byproduct_ids.product_qty = 0.0
        self.warehouse.manufacture_steps = 'pbm_sam'
        mo = self.env["mrp.production"].create({
            'product_id': self.product_a.id,
            'product_qty': 1.0,
            'bom_id': self.bom_byproduct.id,
        })
        mo.action_confirm()
        mo.move_byproduct_ids.quantity = 1.0
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        picking = mo.picking_ids.filtered(lambda p: p.location_dest_id == self.warehouse.lot_stock_id)
        self.assertEqual(picking.state, 'assigned')
        byproduct_move = picking.move_ids.filtered(lambda m: m.product_id == self.bom_byproduct.byproduct_ids.product_id)
        self.assertEqual(byproduct_move.product_qty, 1.0)
