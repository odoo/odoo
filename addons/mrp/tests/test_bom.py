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
            'sequence_id': self.env['ir.sequence'].create({
                'code': 'mrp.production',
                'name': 'tmp_production_sequence',
            }).id,
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

    def test_multi_level_variants2(self):
        """Test skip bom line with same attribute values in bom lines."""

        Product = self.env['product.product']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']
        MrpProduction = self.env['mrp.production']

        # Product Attribute
        att_color = ProductAttribute.create({'name': 'Color'})
        att_size = ProductAttribute.create({'name': 'size'})

        # Product Attribute color Value
        att_color_red = ProductAttributeValue.create({'name': 'red', 'attribute_id': att_color.id})
        att_color_blue = ProductAttributeValue.create({'name': 'blue', 'attribute_id': att_color.id})
        # Product Attribute size Value
        att_size_big = ProductAttributeValue.create({'name': 'big', 'attribute_id': att_size.id})
        att_size_medium = ProductAttributeValue.create({'name': 'medium', 'attribute_id': att_size.id})

        # Create Template Product
        product_template = self.env['product.template'].create({
            'name': 'Sofa',
            'attribute_line_ids': [(0, 0, {
                    'attribute_id': att_color.id,
                    'value_ids': [(6, 0, [att_color_red.id, att_color_blue.id])]
                }), (0, 0, {
                    'attribute_id': att_size.id,
                    'value_ids': [(6, 0, [att_size_big.id, att_size_medium.id])]
                })]
        })

        # Create components Of BOM
        product_A = Product.create({
            'name': 'Wood'})
        product_B = Product.create({
            'name': 'Clothes'})

        # Create BOM
        test_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [(0, 0, {
                    'product_id': product_A.id,
                    'product_qty': 1,
                    'attribute_value_ids': [(4, att_color_red.id), (4, att_color_blue.id), (4, att_size_big.id)],
                }), (0, 0, {
                    'product_id': product_B.id,
                    'product_qty': 1,
                    'attribute_value_ids': [(4, att_color_red.id), (4, att_color_blue.id)]
                })]
        })

        combination = {(att_color_red, att_size_big): [product_A.id, product_B.id] , (att_color_red, att_size_medium): [product_B.id] , (att_color_blue, att_size_big):[product_A.id, product_B.id], (att_color_blue, att_size_medium): [product_B.id]}

        # Create production order for all variants.
        for comb in combination.keys():
            consu_product_ids = combination[comb]
            product = product_template.product_variant_ids.filtered(lambda x:  all(value in comb for value in x.attribute_value_ids))
            mrp_order = MrpProduction.create({
                    'product_uom_id': product.uom_id.id,
                    'product_id': product.id,
                    'bom_id': test_bom.id,
                })
            # Check consumed materials in production order.
            self.assertEqual(mrp_order.move_raw_ids.mapped('product_id').ids, consu_product_ids)

    def test_update_bom(self):
        """Update a BoM used in open production should raise an error"""
        mo = self.env['mrp.production'].create({
            'name': 'MO 1',
            'product_id': self.product_1.id,
            'product_uom_id': self.product_1.uom_id.id,
            'product_qty': 2,
            'bom_id': self.bom_1.id,
        })
        mo.button_plan()
        # update an authorized field
        self.bom_1.write({'code': 'Hello'})
        # update a not authorized field
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.write({'product_id': self.product_2.id})
