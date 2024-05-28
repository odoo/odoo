from odoo import Command
from odoo.addons.stock.tests.test_mtso import TestStockMtso


class TestMrpMtso(TestStockMtso):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.route_manufacture = cls.warehouse_1s.manufacture_pull_id.route_id.id
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')

        # Restore old 'pull' manufacture rules
        cls.warehouse_2s.write({'manufacture_steps': 'pbm'})
        cls.warehouse_3s.write({'manufacture_steps': 'pbm_sam'})
        for wh in [cls.warehouse_2s, cls.warehouse_3s]:
            wh_prod_rule = cls.route_mtso.rule_ids.filtered(
                lambda r:
                    r.location_src_id.id == wh.lot_stock_id.id
                    and r.location_dest_id.id == wh._get_production_location().id
            )
            wh_prod_rule.write({'location_src_id': wh.pbm_loc_id.id})
            cls.env['stock.rule'].create({
                'warehouse_id': wh.id,
                'procure_method': 'mts_else_mto',
                'company_id': wh.company_id.id,
                'action': 'pull',
                'auto': 'manual',
                'route_id': cls.route_mtso.id,
                'name': wh._format_rulename(wh.lot_stock_id, wh.pbm_loc_id, False),
                'location_dest_id': wh.pbm_loc_id.id,
                'location_src_id': wh.lot_stock_id.id,
                'picking_type_id': wh.pbm_type_id.id
            })

        cls.warehouse_3s.manufacture_pull_id.write({'location_dest_id': wh.sam_loc_id.id})
        cls.env['stock.rule'].create({
            'warehouse_id': cls.warehouse_3s.id,
            'procure_method': 'mts_else_mto',  # Directly enhance to MTSO for upcoming tests
            'company_id': cls.warehouse_3s.company_id.id,
            'action': 'pull',
            'auto': 'manual',
            'route_id': cls.route_manufacture,
            'name': cls.warehouse_3s._format_rulename(cls.warehouse_3s.sam_loc_id, cls.warehouse_3s.lot_stock_id, False),
            'location_dest_id': cls.warehouse_3s.lot_stock_id.id,
            'location_src_id': cls.warehouse_3s.sam_loc_id.id,
            'picking_type_id': cls.warehouse_3s.sam_type_id.id
        })

        # products
        cls.simple_product = cls.ProductObj.create({
            'name': 'Product M',
            'route_ids': [Command.link(cls.route_mtso.id), Command.link(cls.route_manufacture)],
            'is_storable': True,
        })
        cls.complex_product = cls.ProductObj.create({
            'name': 'Product MI',
            'route_ids': [Command.link(cls.route_mtso.id), Command.link(cls.route_manufacture)],
            'is_storable': True,
        })
        cls.intermediate_product = cls.ProductObj.create({
            'name': 'Product I',
            'route_ids': [Command.link(cls.route_mtso.id), Command.link(cls.route_manufacture)],
            'is_storable': True,
        })
        cls.simple_raw = cls.ProductObj.create({
            'name': 'raw M',
            'is_storable': False,
        })
        cls.intermediate_raw = cls.ProductObj.create({
            'name': 'raw I',
            'is_storable': False,
        })

        # Create bom for all products
        cls.simple_bom = cls.env['mrp.bom'].create({
            'product_id': cls.simple_product.id,
            'product_tmpl_id': cls.simple_product.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({'product_id': cls.simple_raw.id})]
        })
        cls.intermediate_bom = cls.env['mrp.bom'].create({
            'product_id': cls.intermediate_product.id,
            'product_tmpl_id': cls.intermediate_product.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({'product_id': cls.intermediate_raw.id})]
        })
        cls.complex_bom = cls.env['mrp.bom'].create({
            'product_id': cls.complex_product.id,
            'product_tmpl_id': cls.complex_product.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({'product_id': cls.intermediate_product.id})]
        })

    def test_mtso_mo_mo_1step(self):
        # complex product -> intermediate product
        warehouse = self.warehouse_1s
        self.env['stock.quant']._update_available_quantity(self.intermediate_product, warehouse.lot_stock_id, 3)
        mo = self.env['mrp.production'].create({
            'product_id': self.complex_product.id,
            'product_qty': 10,
            'product_uom_id': self.complex_product.uom_id.id,
            'picking_type_id': warehouse.manu_type_id.id,
        })
        mo.action_confirm()
        mo2 = mo._get_children()
        self.assertAlmostEqual(mo.move_raw_ids[0].quantity, 3, 3)
        self.assertAlmostEqual(mo2.product_qty, 7, 3)
        # Change production qty of mo from 10 to 8
        self.env['change.production.qty'].sudo().with_context(skip_activity=True).create({
            'mo_id': mo.id,
            'product_qty': 8,
        }).change_prod_qty()
        self.assertAlmostEqual(mo2.product_qty, 5, 3)
        mo2.action_confirm()
        mo2.button_mark_done()
        self.assertEqual(mo2.state, 'done')
        self.assertAlmostEqual(mo.move_raw_ids[0].quantity, 8, 3)
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_mtso_mo_mos_1step(self):
        # Add Product M in addition to already set Product I to BoM of Product MI
        self.env['mrp.bom.line'].create({
            'product_id': self.simple_product.id,
            'bom_id': self.complex_bom.id,
            'product_qty': 2,
        })
        warehouse = self.warehouse_1s
        self.env['stock.quant']._update_available_quantity(self.intermediate_product, warehouse.lot_stock_id, 3)
        self.env['stock.quant']._update_available_quantity(self.simple_product, warehouse.lot_stock_id, 5)
        mo = self.env['mrp.production'].create({
            'product_id': self.complex_product.id,
            'product_qty': 10,
            'product_uom_id': self.complex_product.uom_id.id,
            'picking_type_id': warehouse.manu_type_id.id,
        })
        mo.action_confirm()
        mo2, mo3 = mo._get_children()
        self.assertAlmostEqual(mo.move_raw_ids[0].quantity, 3, 3)
        self.assertAlmostEqual(mo.move_raw_ids[1].quantity, 5, 3)
        self.assertAlmostEqual(mo2.product_qty, 7, 3)
        self.assertAlmostEqual(mo3.product_qty, 15, 3)

        mo2.action_confirm()
        mo2.button_mark_done()
        self.assertEqual(mo2.state, 'done')
        self.assertAlmostEqual(mo.move_raw_ids[0].quantity, 10, 3)

        mo3.action_confirm()
        mo3.button_mark_done()
        self.assertEqual(mo3.state, 'done')
        self.assertAlmostEqual(mo.move_raw_ids[1].quantity, 20, 3)
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_mtso_mo_mo_3steps(self):
        warehouse = self.warehouse_3s
        self.env['stock.quant']._update_available_quantity(self.intermediate_product, warehouse.lot_stock_id, 3)
        self.env['stock.quant']._update_available_quantity(self.intermediate_product, warehouse.pbm_loc_id, 2)
        mo = self.env['mrp.production'].create({
            'product_id': self.complex_product.id,
            'product_qty': 10,
            'product_uom_id': self.complex_product.uom_id.id,
            'picking_type_id': warehouse.manu_type_id.id,
        })
        mo.action_confirm()
        pbm_pick = mo.picking_ids[0]
        mo2 = mo._get_children()
        pbm_pick2, sam_pick2 = mo2.picking_ids
        self.assertAlmostEqual(mo.move_raw_ids[0].product_qty_available, 5, 3)
        self.assertAlmostEqual(mo.move_raw_ids[0].quantity, 2, 3)
        self.assertAlmostEqual(pbm_pick.move_ids[0].product_qty, 8, 3)
        self.assertAlmostEqual(pbm_pick.move_ids[0].quantity, 3, 3)
        self.assertAlmostEqual(mo2.product_qty, 5, 3)
        # Change production qty of mo from 10 to 8
        self.env['change.production.qty'].sudo().with_context(skip_activity=True).create({
            'mo_id': mo.id,
            'product_qty': 8,
        }).change_prod_qty()
        self.assertAlmostEqual(pbm_pick.move_ids[0].product_qty, 6, 3)
        self.assertAlmostEqual(mo2.product_qty, 3, 3)
        mo2.action_confirm()
        pbm_pick2.button_validate()
        mo2.button_mark_done()
        self.assertEqual(mo2.state, 'done')
        self.assertTrue(sam_pick2.button_validate())
        self.assertAlmostEqual(pbm_pick.move_ids[0].quantity, 6, 3)
        self.assertTrue(pbm_pick.button_validate())
        self.assertAlmostEqual(mo.move_raw_ids[0].quantity, 8, 3)
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')
        sam_pick = mo.picking_ids - pbm_pick
        self.assertAlmostEqual(sam_pick.move_ids[0].quantity, 8, 3)
        self.assertTrue(sam_pick.button_validate())
