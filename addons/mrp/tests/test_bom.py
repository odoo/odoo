# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.mrp.tests.common import TestMrpCommon


class TestBoM(TestMrpCommon):

    def test_explode(self):
        boms, lines = self.bom_1.explode(self.product_4, 3)
        self.assertEqual(set([bom[0].id for bom in boms]), set(self.bom_1.ids))
        self.assertEqual(set([line[0].id for line in lines]), set(self.bom_1.bom_line_ids.ids))

        boms, lines = self.bom_3.explode(self.product_6, 3)
        self.assertEqual(set([bom[0].id for bom in boms]), set((self.bom_2 | self.bom_3).ids))
        self.assertEqual(
            set([line[0].id for line in lines]),
            set((self.bom_2 | self.bom_3).mapped('bom_line_ids').filtered(lambda line: not line.child_bom_id or line.child_bom_id.type != 'phantom').ids))

    def test_variants(self):
        test_bom = self.env['mrp.bom'].create({
            'product_id': self.product_7.id,
            'product_tmpl_id': self.product_7.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'routing_id': self.routing_2.id,
            'type': 'normal',
        })
        test_bom_l1 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom.id,
            'product_id': self.product_2.id,
            'product_qty': 2,
        })
        test_bom_l2 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom.id,
            'product_id': self.product_3.id,
            'product_qty': 2,
            'attribute_value_ids': [(4, self.prod_attr1_v1.id)],
        })
        test_bom_l3 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom.id,
            'product_id': self.product_4.id,
            'product_qty': 2,
            'attribute_value_ids': [(4, self.prod_attr1_v2.id)],
        })
        boms, lines = test_bom.explode(self.product_7, 4)
        self.assertIn(test_bom, [b[0]for b in boms])
        self.assertIn(test_bom_l1, [l[0] for l in lines])
        self.assertNotIn(test_bom_l2, [l[0] for l in lines])
        self.assertNotIn(test_bom_l3, [l[0] for l in lines])

        boms, lines = test_bom.explode(self.product_7_1, 4)
        self.assertIn(test_bom, [b[0]for b in boms])
        self.assertIn(test_bom_l1, [l[0] for l in lines])
        self.assertIn(test_bom_l2, [l[0] for l in lines])
        self.assertNotIn(test_bom_l3, [l[0] for l in lines])

        boms, lines = test_bom.explode(self.product_7_2, 4)
        self.assertIn(test_bom, [b[0]for b in boms])
        self.assertIn(test_bom_l1, [l[0] for l in lines])
        self.assertNotIn(test_bom_l2, [l[0] for l in lines])
        self.assertIn(test_bom_l3, [l[0] for l in lines])

    def test_multi_level_variants(self):
        tmp_picking_type = self.env['stock.picking.type'].create({
            'name': 'Manufacturing',
            'code': 'mrp_operation',
            'sequence_id': self.env['ir.sequence'].search([('code', '=', 'mrp.production')], limit=1).id,
        })
        test_bom_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_5.product_tmpl_id.id,
            'product_uom_id': self.product_5.uom_id.id,
            'product_qty': 1.0,
            'routing_id': self.routing_1.id,
            'type': 'phantom'
        })
        test_bom_1_l1 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_1.id,
            'product_id': self.product_3.id,
            'product_qty': 3,
        })

        test_bom_2 = self.env['mrp.bom'].create({
            'product_id': self.product_7.id,
            'product_tmpl_id': self.product_7.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'routing_id': self.routing_2.id,
            'type': 'normal',
        })
        test_bom_2_l1 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_2.id,
            'product_id': self.product_2.id,
            'product_qty': 2,
        })
        test_bom_2_l2 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_2.id,
            'product_id': self.product_5.id,
            'product_qty': 2,
            'attribute_value_ids': [(4, self.prod_attr1_v1.id)],
        })
        test_bom_2_l3 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_2.id,
            'product_id': self.product_5.id,
            'product_qty': 2,
            'attribute_value_ids': [(4, self.prod_attr1_v2.id)],
        })
        test_bom_2_l4 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_2.id,
            'product_id': self.product_4.id,
            'product_qty': 2,
        })

        # check product > product_tmpl
        boms, lines = test_bom_2.explode(self.product_7_1, 4)
        self.assertEqual(set((test_bom_2 | self.bom_2).ids), set([b[0].id for b in boms]))
        self.assertEqual(set((test_bom_2_l1 | test_bom_2_l4 | self.bom_2.bom_line_ids).ids), set([l[0].id for l in lines]))

        # check sequence priority
        test_bom_1.write({'sequence': 1})
        boms, lines = test_bom_2.explode(self.product_7_1, 4)
        self.assertEqual(set((test_bom_2 | test_bom_1).ids), set([b[0].id for b in boms]))
        self.assertEqual(set((test_bom_2_l1 | test_bom_2_l4 | test_bom_1.bom_line_ids).ids), set([l[0].id for l in lines]))

        # check with another picking_type
        test_bom_1.write({'picking_type_id': self.warehouse_1.manu_type_id.id})
        self.bom_2.write({'picking_type_id': tmp_picking_type.id})
        test_bom_2.write({'picking_type_id': tmp_picking_type.id})
        boms, lines = test_bom_2.explode(self.product_7_1, 4)
        self.assertEqual(set((test_bom_2 | self.bom_2).ids), set([b[0].id for b in boms]))
        self.assertEqual(set((test_bom_2_l1 | test_bom_2_l4 | self.bom_2.bom_line_ids).ids), set([l[0].id for l in lines]))

        #check recursion
        test_bom_3 = self.env['mrp.bom'].create({
            'product_id': self.product_9.id,
            'product_tmpl_id': self.product_9.product_tmpl_id.id,
            'product_uom_id': self.product_9.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal'
        })
        test_bom_4 = self.env['mrp.bom'].create({
            'product_id': self.product_10.id,
            'product_tmpl_id': self.product_10.product_tmpl_id.id,
            'product_uom_id': self.product_10.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom'
        })
        test_bom_3_l1 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_3.id,
            'product_id': self.product_10.id,
            'product_qty': 1.0,
        })
        test_bom_4_l1 = self.env['mrp.bom.line'].create({
            'bom_id': test_bom_4.id,
            'product_id': self.product_9.id,
            'product_qty': 1.0,
        })
        with self.assertRaises(exceptions.UserError):
            test_bom_3.explode(self.product_9, 1)
