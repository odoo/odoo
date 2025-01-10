# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions, Command, fields
from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests.common import HttpCase, tagged, freeze_time
from odoo.tools import float_compare, float_round, float_repr


@freeze_time(fields.Date.today())
class TestBoM(TestMrpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._enable_product_variant(cls.user_stock_user)

    def test_01_explode(self):
        boms, lines = self.bom_1.explode(self.product_4, 3)
        self.assertEqual(set([bom[0].id for bom in boms]), set(self.bom_1.ids))
        self.assertEqual(set([line[0].id for line in lines]), set(self.bom_1.bom_line_ids.ids))

        boms, lines = self.bom_3.explode(self.product_6, 3)
        self.assertEqual(set([bom[0].id for bom in boms]), set((self.bom_2 | self.bom_3).ids))
        self.assertEqual(
            set([line[0].id for line in lines]),
            set((self.bom_2 | self.bom_3).mapped('bom_line_ids').filtered(lambda line: not line.child_bom_id or line.child_bom_id.type != 'phantom').ids))

    def test_10_variants(self):
        test_bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'type': 'normal',
            'operation_ids': [
                Command.create({
                    'name': 'Cutting Machine',
                    'workcenter_id': self.workcenter_1.id,
                    'time_cycle': 12,
                    'sequence': 1
                }),
                Command.create({
                    'name': 'Weld Machine',
                    'workcenter_id': self.workcenter_1.id,
                    'time_cycle': 18,
                    'sequence': 2,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v1.id)]
                }),
                Command.create({
                    'name': 'Taking a coffee',
                    'workcenter_id': self.workcenter_1.id,
                    'time_cycle': 5,
                    'sequence': 3,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v2.id)]
                })
            ],
            'byproduct_ids': [
                Command.create({
                    'product_id': self.product_1.id,
                    'product_uom_id': self.product_1.uom_id.id,
                    'product_qty': 1,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_uom_id': self.product_2.uom_id.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v1.id)]
                }),
                Command.create({
                    'product_id': self.product_3.id,
                    'product_uom_id': self.product_3.uom_id.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v2.id)]
                }),
            ],
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 2,
                }),
                Command.create({
                    'product_id': self.product_3.id,
                    'product_qty': 2,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v1.id)],
                }),
                Command.create({
                    'product_id': self.product_4.id,
                    'product_qty': 2,
                    'bom_product_template_attribute_value_ids': [Command.link(self.product_7_attr1_v2.id)],
                }),
            ]
        })
        test_bom_l1, test_bom_l2, test_bom_l3 = test_bom.bom_line_ids
        boms, lines = test_bom.explode(self.product_7_3, 4)
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

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.product_7_3
        mrp_order = mrp_order_form.save()
        self.assertEqual(mrp_order.bom_id, test_bom)
        self.assertEqual(len(mrp_order.workorder_ids), 1)
        self.assertEqual(mrp_order.workorder_ids.operation_id, test_bom.operation_ids[0])
        self.assertEqual(len(mrp_order.move_byproduct_ids), 1)
        self.assertEqual(mrp_order.move_byproduct_ids.product_id, self.product_1)

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.product_7_1
        mrp_order_form.product_id = self.env['product.product']  # Check form
        mrp_order_form.product_id = self.product_7_1
        mrp_order_form.bom_id = self.env['mrp.bom']  # Check form
        mrp_order_form.bom_id = test_bom
        mrp_order = mrp_order_form.save()
        self.assertEqual(mrp_order.bom_id, test_bom)
        self.assertEqual(len(mrp_order.workorder_ids), 2)
        self.assertEqual(mrp_order.workorder_ids.operation_id, test_bom.operation_ids[:2])
        self.assertEqual(len(mrp_order.move_byproduct_ids), 2)
        self.assertEqual(mrp_order.move_byproduct_ids.product_id, self.product_1 | self.product_2)

        mrp_order_form = Form(self.env['mrp.production'])
        mrp_order_form.product_id = self.product_7_2
        mrp_order = mrp_order_form.save()
        self.assertEqual(mrp_order.bom_id, test_bom)
        self.assertEqual(len(mrp_order.workorder_ids), 2)
        self.assertEqual(mrp_order.workorder_ids.operation_id, test_bom.operation_ids[0] | test_bom.operation_ids[2])
        self.assertEqual(len(mrp_order.move_byproduct_ids), 2)
        self.assertEqual(mrp_order.move_byproduct_ids.product_id, self.product_1 | self.product_3)

    def test_11_multi_level_variants(self):
        tmp_picking_type = self.PickingTypeObj.create({
            'name': 'Manufacturing',
            'code': 'mrp_operation',
            'sequence_code': 'TMP',
        })
        test_bom_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_5.product_tmpl_id.id,
            'product_uom_id': self.product_5.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom'
        })
        test_bom_1.write({
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
        })
        test_bom_1.bom_line_ids = [(0, 0, {
            'product_id': self.product_3.id,
            'product_qty': 3,
        })]

        test_bom_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'type': 'normal',
        })
        test_bom_2.write({
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                (0, 0, {'name': 'Weld Machine', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 18, 'sequence': 2}),
            ]
        })
        test_bom_2.bom_line_ids = [(0, 0, {
            'product_id': self.product_2.id,
            'product_qty': 2,
        })]
        test_bom_2.bom_line_ids = [(0, 0, {
            'product_id': self.product_5.id,
            'product_qty': 2,
            'bom_product_template_attribute_value_ids': [(4, self.product_7_attr1_v1.id)],
        })]
        test_bom_2.bom_line_ids = [(0, 0, {
            'product_id': self.product_5.id,
            'product_qty': 2,
            'bom_product_template_attribute_value_ids': [(4, self.product_7_attr1_v2.id)],
        })]
        test_bom_2.bom_line_ids = [(0, 0, {
            'product_id': self.product_4.id,
            'product_qty': 2,
        })]
        test_bom_2_l1, _test_bom_2_l2, _test_bom_2_l3, test_bom_2_l4 = test_bom_2.bom_line_ids

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

        self.product_9, self.product_10 = self.env['product.product'].create([{
            'name': 'Paper',  # product_9
        }, {
            'name': 'Stone',  # product_10
        }])

        #check recursion
        test_bom_3 = self.env['mrp.bom'].create({
            'product_id': self.product_9.id,
            'product_tmpl_id': self.product_9.product_tmpl_id.id,
            'product_uom_id': self.product_9.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'normal'
        })
        test_bom_4 = self.env['mrp.bom'].create({
            'product_id': self.product_10.id,
            'product_tmpl_id': self.product_10.product_tmpl_id.id,
            'product_uom_id': self.product_10.uom_id.id,
            'product_qty': 1.0,
            'consumption': 'flexible',
            'type': 'phantom'
        })
        test_bom_3.bom_line_ids = [(0, 0, {
            'product_id': self.product_10.id,
            'product_qty': 1.0,
        })]
        with self.assertRaises(exceptions.UserError):
            test_bom_4.bom_line_ids = [(0, 0, {
                'product_id': self.product_9.id,
                'product_qty': 1.0,
            })]

    def test_12_multi_level_variants2(self):
        """Test skip bom line with same attribute values in bom lines."""

        Product = self.env['product.product']
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']

        # Product Attribute
        att_color = ProductAttribute.create({'name': 'Color', 'sequence': 1})
        att_size = ProductAttribute.create({'name': 'size', 'sequence': 2})

        # Product Attribute color Value
        att_color_red = ProductAttributeValue.create({'name': 'red', 'attribute_id': att_color.id, 'sequence': 1})
        att_color_blue = ProductAttributeValue.create({'name': 'blue', 'attribute_id': att_color.id, 'sequence': 2})
        # Product Attribute size Value
        att_size_big = ProductAttributeValue.create({'name': 'big', 'attribute_id': att_size.id, 'sequence': 1})
        att_size_medium = ProductAttributeValue.create({'name': 'medium', 'attribute_id': att_size.id, 'sequence': 2})

        # Create Template Product
        product_template = self.env['product.template'].create({
            'name': 'Sofa',
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': att_color.id,
                    'value_ids': [(6, 0, [att_color_red.id, att_color_blue.id])]
                }),
                (0, 0, {
                    'attribute_id': att_size.id,
                    'value_ids': [(6, 0, [att_size_big.id, att_size_medium.id])]
                })
            ]
        })

        sofa_red = product_template.attribute_line_ids[0].product_template_value_ids[0]
        sofa_blue = product_template.attribute_line_ids[0].product_template_value_ids[1]

        sofa_big = product_template.attribute_line_ids[1].product_template_value_ids[0]
        sofa_medium = product_template.attribute_line_ids[1].product_template_value_ids[1]

        # Create components Of BOM
        product_A = Product.create({
            'name': 'Wood'})
        product_B = Product.create({
            'name': 'Clothes'})

        # Create BOM
        self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': product_A.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [(4, sofa_red.id), (4, sofa_blue.id), (4, sofa_big.id)],
                }),
                (0, 0, {
                    'product_id': product_B.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [(4, sofa_red.id), (4, sofa_blue.id)]
                })
            ]
        })

        dict_consumed_products = {
            sofa_red + sofa_big: product_A + product_B,
            sofa_red + sofa_medium: product_B,
            sofa_blue + sofa_big: product_A + product_B,
            sofa_blue + sofa_medium: product_B,
        }

        # Create production order for all variants.
        for combination, consumed_products in dict_consumed_products.items():
            product = product_template.product_variant_ids.filtered(lambda p: p.product_template_attribute_value_ids == combination)
            mrp_order_form = Form(self.env['mrp.production'])
            mrp_order_form.product_id = product
            mrp_order = mrp_order_form.save()

            # Check consumed materials in production order.
            self.assertEqual(mrp_order.move_raw_ids.product_id, consumed_products)

    def test_13_bom_kit_qty(self):
        self.env['mrp.bom'].create({
            'product_id': self.product_7_3.id,
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_2.id,
                    'product_qty': 2,
                }),
                (0, 0, {
                    'product_id': self.product_3.id,
                    'product_qty': 2,
                })
            ]
        })
        self.env['stock.quant']._update_available_quantity(self.product_2, self.stock_location, 4.0)
        self.env['stock.quant']._update_available_quantity(self.product_3, self.stock_location, 8.0)
        # Force the kit product available qty to be computed at the same time than its component quantities
        # Because `qty_available` of a bom kit "recurse" on `qty_available` of its component,
        # and this is a tricky thing for the ORM:
        # `qty_available` gets called for `product_7_3`, `product_2` and `product_3`
        # which then recurse on calling `qty_available` for `product_2` and `product_3` to compute the quantity of
        # the kit `product_7_3`. `product_2` and `product_3` gets protected at the first call of the compute method,
        # ending the recurse call to not call the compute method and just left the Falsy value `0.0`
        # for the components available qty.
        kit_product_qty, _, _ = (self.product_7_3 + self.product_2 + self.product_3).mapped("qty_available")
        self.assertEqual(kit_product_qty, 8)

    def test_14_bom_kit_qty_multi_uom(self):
        product_unit = self.env['product.product'].create({
            'name': 'Test units',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        product_dozens = self.env['product.product'].create({
            'name': 'Test dozens',
            'type': 'consu',
            'is_storable': True,
            'uom_id': self.uom_dozen.id,
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': product_unit.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': product_dozens.id,
                    'product_qty': 1,
                    'product_uom_id': self.uom_unit.id,
                })
            ]
        })
        self.env['stock.quant']._update_available_quantity(product_dozens, self.stock_location, 1.0)
        self.assertEqual(product_unit.qty_available, 12.0)

    def test_13_negative_on_hand_qty(self):
        # We set the Product Unit of Measure digits to 5.
        # Because float_round(-384.0, 5) = -384.00000000000006
        # And float_round(-384.0, 2) = -384.0
        precision_digits = 5
        self.env.ref('product.decimal_product_uom').sudo().digits = precision_digits

        # We set the Unit(s) rounding to 0.0001 (digit = 4)
        self.uom_unit.rounding = 0.0001

        _ = self.env['mrp.bom'].create({
            'product_id': self.product_2.id,
            'product_tmpl_id': self.product_2.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.00,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_3.id,
                    'product_qty': 1.000,
                }),
            ]
        })

        self.env['stock.quant']._update_available_quantity(self.product_3, self.stock_location, -384.0)

        kit_product_qty = self.product_2.qty_available  # Without product_3 in the prefetch
        # Use the float_repr to remove extra small decimal (and represent the front-end behavior)
        self.assertEqual(float_repr(float_round(kit_product_qty, precision_digits=precision_digits), precision_digits=precision_digits), '-384.00000')

        self.product_2.invalidate_recordset(['qty_available'])
        kit_product_qty, _ = (self.product_2 + self.product_3).mapped("qty_available")  # With product_3 in the prefetch
        self.assertEqual(float_repr(float_round(kit_product_qty, precision_digits=precision_digits), precision_digits=precision_digits), '-384.00000')

    def test_13_bom_kit_qty_multi_uom(self):
        product_unit = self.env['product.product'].create({
            'name': 'Test units',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        product_dozens = self.env['product.product'].create({
            'name': 'Test dozens',
            'is_storable': True,
            'uom_id': self.uom_dozen.id,
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': product_unit.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': product_dozens.id,
                    'product_qty': 1,
                    'product_uom_id': self.uom_unit.id,
                })
            ]
        })
        self.env['stock.quant']._update_available_quantity(product_dozens, self.stock_location, 1.0)
        self.assertEqual(product_unit.qty_available, 12.0)

    def test_19_bom_kit_field_is_kits_bom_with_product_id(self):
        kit_products = self.env['product.product'].create({
            'name': 'No Kit',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        self.env['mrp.bom'].create({
            'product_id': kit_products.id,
            'product_tmpl_id': kit_products.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_2.id,
                    'product_qty': 2,
                }),
                (0, 0, {
                    'product_id': self.product_3.id,
                    'product_qty': 2,
                })
            ]
        })
        self.assertTrue(kit_products.is_kits)
        self.assertTrue(kit_products.product_tmpl_id.is_kits)

        no_kit_products = self.env['product.product'].create({
            'name': 'No Kit',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        self.assertFalse(no_kit_products.is_kits)
        self.assertFalse(no_kit_products.product_tmpl_id.is_kits)

        product_with_kit = self.env['product.product'].search(
            [('is_kits', '=', True)])
        product_tmpl_with_kit = self.env['product.template'].search(
            [('is_kits', '=', True)])
        self.assertIn(kit_products, product_with_kit)
        self.assertIn(kit_products.product_tmpl_id, product_tmpl_with_kit)
        self.assertNotIn(no_kit_products, product_with_kit)
        self.assertNotIn(no_kit_products.product_tmpl_id,
                         product_tmpl_with_kit)

        product_without_kit = self.env['product.product'].search(
            [('is_kits', '=', False)])
        product_tmpl_without_kit = self.env['product.template'].search(
            [('is_kits', '=', False)])
        self.assertIn(no_kit_products, product_without_kit)
        self.assertIn(no_kit_products.product_tmpl_id,
                      product_tmpl_without_kit)
        self.assertNotIn(kit_products, product_without_kit)
        self.assertNotIn(kit_products.product_tmpl_id,
                         product_tmpl_without_kit)

    def test_19_bom_kit_field_is_kits_bom_without_product_id(self):
        kit_products = self.env['product.product'].create({
            'name': 'No Kit',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        self.env['mrp.bom'].create({
            'product_tmpl_id': kit_products.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 4.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_2.id,
                    'product_qty': 2,
                }),
                (0, 0, {
                    'product_id': self.product_3.id,
                    'product_qty': 2,
                })
            ]
        })
        self.assertTrue(kit_products.is_kits)
        self.assertTrue(kit_products.product_tmpl_id.is_kits)

        no_kit_products = self.env['product.product'].create({
            'name': 'No Kit',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        self.assertFalse(no_kit_products.is_kits)
        self.assertFalse(no_kit_products.product_tmpl_id.is_kits)

        product_with_kit = self.env['product.product'].search(
            [('is_kits', '=', True)])
        product_tmpl_with_kit = self.env['product.template'].search(
            [('is_kits', '=', True)])
        self.assertIn(kit_products, product_with_kit)
        self.assertIn(kit_products.product_tmpl_id, product_tmpl_with_kit)
        self.assertNotIn(no_kit_products, product_with_kit)
        self.assertNotIn(no_kit_products.product_tmpl_id,
                         product_tmpl_with_kit)

        product_without_kit = self.env['product.product'].search(
            [('is_kits', '=', False)])
        product_tmpl_without_kit = self.env['product.template'].search(
            [('is_kits', '=', False)])
        self.assertIn(no_kit_products, product_without_kit)
        self.assertIn(no_kit_products.product_tmpl_id,
                      product_tmpl_without_kit)
        self.assertNotIn(kit_products, product_without_kit)
        self.assertNotIn(kit_products.product_tmpl_id,
                         product_tmpl_without_kit)

    def test_20_bom_report(self):
        """ Simulate a crumble receipt with mrp and open the bom structure
        report and check that data insde are correct.
        """
        uom_kg = self.env.ref('uom.product_uom_kgm')
        uom_litre = self.env.ref('uom.product_uom_litre')
        crumble = self.env['product.product'].create({
            'name': 'Crumble',
            'is_storable': True,
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
        })
        butter = self.env['product.product'].create({
            'name': 'Butter',
            'is_storable': True,
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
            'standard_price': 7.01
        })
        biscuit = self.env['product.product'].create({
            'name': 'Biscuit',
            'is_storable': True,
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
            'standard_price': 1.5
        })
        bom_form_crumble = Form(self.env['mrp.bom'])
        bom_form_crumble.product_tmpl_id = crumble.product_tmpl_id
        bom_form_crumble.product_qty = 11
        bom_form_crumble.product_uom_id = uom_kg
        bom_crumble = bom_form_crumble.save()

        workcenter = self.env['mrp.workcenter'].create({
            'costs_hour': 10,
            'name': 'Deserts Table'
        })

        with Form(bom_crumble) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = butter
                line.product_uom_id = uom_kg
                line.product_qty = 5
            with bom.bom_line_ids.new() as line:
                line.product_id = biscuit
                line.product_uom_id = uom_kg
                line.product_qty = 6
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Prepare biscuits'
                operation.time_cycle_manual = 5
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Prepare butter'
                operation.time_cycle_manual = 3
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Mix manually'
                operation.time_cycle_manual = 5

        # TEST BOM STRUCTURE VALUE WITH BOM QUANTITY
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=11, searchVariant=False)
        # 5 min 'Prepare biscuits' + 3 min 'Prepare butter' + 5 min 'Mix manually' = 13 minutes for 1 biscuits so 13 * 11 = 143 minutes
        self.assertEqual(report_values['lines']['operations_time'], 143.0, 'Operation time should be the same for 1 unit or for the batch')
        # Operation cost is the sum of operation line.
        self.assertEqual(float_compare(report_values['lines']['operations_cost'], 23.84, precision_digits=2), 0, '143 minute for 10$/hours -> 23.84')

        for component_line in report_values['lines']['components']:
            # standard price * bom line quantity * current quantity / bom finished product quantity
            if component_line['product'].id == butter.id:
                # 5 kg of butter at 7.01$ for 11kg of crumble -> 35.05$
                self.assertEqual(float_compare(component_line['bom_cost'], (7.01 * 5), precision_digits=2), 0)
            if component_line['product'].id == biscuit.id:
                # 6 kg of biscuits at 1.50$ for 11kg of crumble -> 9$
                self.assertEqual(float_compare(component_line['bom_cost'], (1.5 * 6), precision_digits=2), 0)
        # total price = 35.05 + 9 + operation_cost(23.84) = 67.89
        self.assertEqual(float_compare(report_values['lines']['bom_cost'], 67.89, precision_digits=2), 0, 'Product Bom Price is not correct')
        self.assertEqual(float_compare(report_values['lines']['bom_cost'] / 11.0, 6.17, precision_digits=2), 0, 'Product Unit Bom Price is not correct')

        # TEST BOM STRUCTURE VALUE BY UNIT
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=1, searchVariant=False)
        # 5 min 'Prepare biscuits' + 3 min 'Prepare butter' + 5 min 'Mix manually' = 13 minutes
        self.assertEqual(report_values['lines']['operations_time'], 13.0, 'Operation time should be the same for 1 unit or for the batch')
        # Operation cost is the sum of operation line.
        operation_cost = float_round(5 / 60 * 10, precision_digits=2) * 2 + float_round(3 / 60 * 10, precision_digits=2)
        self.assertEqual(float_compare(report_values['lines']['operations_cost'], operation_cost, precision_digits=2), 0, '13 minute for 10$/hours -> 2.16')

        for component_line in report_values['lines']['components']:
            # standard price * bom line quantity * current quantity / bom finished product quantity
            if component_line['product'].id == butter.id:
                # 5 kg of butter at 7.01$ for 11kg of crumble -> / 11 for price per unit (3.19)
                self.assertEqual(float_compare(component_line['bom_cost'], (7.01 * 5) * (1 / 11), precision_digits=2), 0)
            if component_line['product'].id == biscuit.id:
                # 6 kg of biscuits at 1.50$ for 11kg of crumble -> / 11 for price per unit (0.82)
                self.assertEqual(float_compare(component_line['bom_cost'], (1.5 * 6) * (1 / 11), precision_digits=2), 0)
        # total price = 3.19 + 0.82 + operation_cost(0.83 + 0.83 + 0.5 = 2.16) = 6,17
        self.assertEqual(float_compare(report_values['lines']['bom_cost'], 6.17, precision_digits=2), 0, 'Product Unit Bom Price is not correct')

        # TEST OPERATION COST WHEN PRODUCED QTY > BOM QUANTITY
        report_values_12 = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=12, searchVariant=False)
        report_values_22 = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=22, searchVariant=False)

        #Operation cost = 47.66 € = 256 (min) * 10€/h
        self.assertEqual(float_compare(report_values_22['lines']['operations_cost'], 47.66, precision_digits=2), 0, 'Operation cost is not correct')

        # Create a more complex BoM with a sub product
        cheese_cake = self.env['product.product'].create({
            'name': 'Cheese Cake 300g',
            'is_storable': True,
        })
        cream = self.env['product.product'].create({
            'name': 'cream',
            'is_storable': True,
            'uom_id': uom_litre.id,
            'uom_po_id': uom_litre.id,
            'standard_price': 5.17,
        })
        bom_form_cheese_cake = Form(self.env['mrp.bom'])
        bom_form_cheese_cake.product_tmpl_id = cheese_cake.product_tmpl_id
        bom_form_cheese_cake.product_qty = 60
        bom_form_cheese_cake.product_uom_id = self.uom_unit
        bom_cheese_cake = bom_form_cheese_cake.save()

        workcenter_2 = self.env['mrp.workcenter'].create({
            'name': 'cake mounting',
            'costs_hour': 20,
            'time_start': 10,
            'time_stop': 15
        })

        self.env['mrp.workcenter.capacity'].create({
            'product_id': cheese_cake.id,
            'workcenter_id': workcenter_2.id,
            'time_start': 12,
            'time_stop': 16,
        })

        with Form(bom_cheese_cake) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cream
                line.product_uom_id = uom_litre
                line.product_qty = 3
            with bom.bom_line_ids.new() as line:
                line.product_id = crumble
                line.product_uom_id = uom_kg
                line.product_qty = 5.4
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Mix cheese and crumble'
                operation.time_cycle_manual = 10
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter_2
                operation.name = 'Cake mounting'
                operation.time_cycle_manual = 5

        # TEST CHEESE BOM STRUCTURE VALUE WITH BOM QUANTITY
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_cheese_cake.id, searchQty=60, searchVariant=False)
        # Operation time = 15 min * 60 + capacity_time_start + capacity_time_stop = 928
        self.assertEqual(report_values['lines']['operations_time'], 928.0, 'Operation time should be the same for 1 unit or for the batch')
        # Operation cost is the sum of operation line : (60 * 10)/60 * 10€ + (10 + 15 + 60 * 5)/60 * 20€ + (1 + 2)/60 * 20€ = 209,33€
        self.assertEqual(float_compare(report_values['lines']['operations_cost'], 209.33, precision_digits=2), 0)

        for component_line in report_values['lines']['components']:
            # standard price * bom line quantity * current quantity / bom finished product quantity
            if component_line['product'].id == cream.id:
                # 3 liter of cream at 5.17$ for 60 unit of cheese cake -> 15.51$
                self.assertEqual(float_compare(component_line['bom_cost'], (3 * 5.17), precision_digits=2), 0)
            if component_line['product'].id == crumble.id:
                # 5.4 kg of crumble at the cost of a batch.
                crumble_cost = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=5.4, searchVariant=False)['lines']['bom_cost']
                self.assertEqual(float_compare(component_line['bom_cost'], crumble_cost, precision_digits=2), 0)
        # total price = Cream (15.51€) + crumble_cost (34.63 €) + operation_cost(209,33) = 259.47€
        self.assertEqual(float_compare(report_values['lines']['bom_cost'], 259.47, precision_digits=2), 0, 'Product Bom Price is not correct')

    def test_bom_report_dozens(self):
        """ Simulate a drawer bom with dozens as bom units
        """
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        uom_unit = self.env.ref('uom.product_uom_unit')
        drawer = self.env['product.product'].create({
            'name': 'drawer',
            'is_storable': True,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })
        screw = self.env['product.product'].create({
            'name': 'screw',
            'is_storable': True,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
            'standard_price': 7.01
        })

        bom_form_drawer = Form(self.env['mrp.bom'])
        bom_form_drawer.product_tmpl_id = drawer.product_tmpl_id
        bom_form_drawer.product_qty = 11
        bom_form_drawer.product_uom_id = uom_dozen
        bom_drawer = bom_form_drawer.save()

        workcenter = self.env['mrp.workcenter'].create({
            'costs_hour': 10,
            'name': 'Deserts Table'
        })

        with Form(bom_drawer) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = screw
                line.product_uom_id = uom_unit
                line.product_qty = 5
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Screw drawer'
                operation.time_cycle_manual = 5

        # TEST BOM STRUCTURE VALUE WITH BOM QUANTITY
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_drawer.id, searchQty=11, searchVariant=False)
        # 5 min 'Prepare biscuits' + 3 min 'Prepare butter' + 5 min 'Mix manually' = 13 minutes
        self.assertEqual(report_values['lines']['operations_time'], 660.0, 'Operation time should be the same for 1 unit or for the batch')

    def test_21_bom_report_variant(self):
        """ Test a sub BoM process with multiple variants.
        BOM 1:
        product template = car
        quantity = 5 units
        - red paint 50l -> red car (product.product)
        - blue paint 50l -> blue car
        - red dashboard with gps -> red car with GPS
        - red dashboard w/h gps -> red w/h GPS
        - blue dashboard with gps -> blue car with GPS
        - blue dashboard w/h gps -> blue w/h GPS

        BOM 2:
        product_tmpl = dashboard
        quantity = 2
        - red paint 1l -> red dashboard (product.product)
        - blue paint 1l -> blue dashboard
        - gps -> dashboard with gps

        Check the Price for a Blue Car with GPS -> 910$:
        10l of blue paint -> 200$
        1 blue dashboard GPS -> 710$:
            - 0.5l of blue paint -> 10$
            - GPS -> 700$

        Check the price for a red car -> 10.5l of red paint -> 210$
        """
        # Create a product template car with attributes gps(yes, no), color(red, blue)
        self.car = self.env['product.template'].create({
            'name': 'Car',
        })
        self.gps_attribute = self.env['product.attribute'].create({'name': 'GPS', 'sequence': 1})
        self.gps_yes = self.env['product.attribute.value'].create({
            'name': 'Yes',
            'attribute_id': self.gps_attribute.id,
            'sequence': 1,
        })
        self.gps_no = self.env['product.attribute.value'].create({
            'name': 'No',
            'attribute_id': self.gps_attribute.id,
            'sequence': 2,
        })

        self.car_gps_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.car.id,
            'attribute_id': self.gps_attribute.id,
            'value_ids': [(6, 0, [self.gps_yes.id, self.gps_no.id])],
        })
        self.car_gps_yes = self.car_gps_attribute_line.product_template_value_ids[0]
        self.car_gps_no = self.car_gps_attribute_line.product_template_value_ids[1]

        self.color_attribute = self.env['product.attribute'].create({'name': 'Color', 'sequence': 1})
        self.color_red = self.env['product.attribute.value'].create({
            'name': 'Red',
            'attribute_id': self.color_attribute.id,
            'sequence': 1,
        })
        self.color_blue = self.env['product.attribute.value'].create({
            'name': 'Blue',
            'attribute_id': self.color_attribute.id,
            'sequence': 2,
        })

        self.car_color_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.car.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id, self.color_blue.id])],
        })
        self.car_color_red = self.car_color_attribute_line.product_template_value_ids[0]
        self.car_color_blue = self.car_color_attribute_line.product_template_value_ids[1]

        # Blue and red paint
        uom_litre = self.env.ref('uom.product_uom_litre')
        self.paint = self.env['product.template'].create({
            'name': 'Paint',
            'uom_id': uom_litre.id,
            'uom_po_id': uom_litre.id
        })
        self.paint_color_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.paint.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id, self.color_blue.id])],
        })
        self.paint_color_red = self.paint_color_attribute_line.product_template_value_ids[0]
        self.paint_color_blue = self.paint_color_attribute_line.product_template_value_ids[1]

        self.paint.product_variant_ids.write({'standard_price': 20})

        self.dashboard = self.env['product.template'].create({
            'name': 'Dashboard',
            'standard_price': 1000,
        })

        self.dashboard_gps_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.dashboard.id,
            'attribute_id': self.gps_attribute.id,
            'value_ids': [(6, 0, [self.gps_yes.id, self.gps_no.id])],
        })
        self.dashboard_gps_yes = self.dashboard_gps_attribute_line.product_template_value_ids[0]
        self.dashboard_gps_no = self.dashboard_gps_attribute_line.product_template_value_ids[1]

        self.dashboard_color_attribute_line = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.dashboard.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id, self.color_blue.id])],
        })
        self.dashboard_color_red = self.dashboard_color_attribute_line.product_template_value_ids[0]
        self.dashboard_color_blue = self.dashboard_color_attribute_line.product_template_value_ids[1]

        self.gps = self.env['product.product'].create({
            'name': 'GPS',
            'standard_price': 700,
        })

        bom_form_car = Form(self.env['mrp.bom'])
        bom_form_car.product_tmpl_id = self.car
        bom_form_car.product_qty = 5
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(self.paint_color_red)
            line.product_uom_id = uom_litre
            line.product_qty = 50
            line.bom_product_template_attribute_value_ids.add(self.car_color_red)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(self.paint_color_blue)
            line.product_uom_id = uom_litre
            line.product_qty = 50
            line.bom_product_template_attribute_value_ids.add(self.car_color_blue)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(self.dashboard_gps_yes + self.dashboard_color_red)
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_yes)
            line.bom_product_template_attribute_value_ids.add(self.car_color_red)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(self.dashboard_gps_yes + self.dashboard_color_blue)
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_yes)
            line.bom_product_template_attribute_value_ids.add(self.car_color_blue)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(self.dashboard_gps_no + self.dashboard_color_red)
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_no)
            line.bom_product_template_attribute_value_ids.add(self.car_color_red)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(self.dashboard_gps_no + self.dashboard_color_blue)
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_no)
            line.bom_product_template_attribute_value_ids.add(self.car_color_blue)
        bom_car = bom_form_car.save()

        bom_dashboard = Form(self.env['mrp.bom'])
        bom_dashboard.product_tmpl_id = self.dashboard
        bom_dashboard.product_qty = 2
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(self.paint_color_red)
            line.product_uom_id = uom_litre
            line.product_qty = 1
            line.bom_product_template_attribute_value_ids.add(self.dashboard_color_red)
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(self.paint_color_blue)
            line.product_uom_id = uom_litre
            line.product_qty = 1
            line.bom_product_template_attribute_value_ids.add(self.dashboard_color_blue)
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.gps
            line.product_qty = 2
            line.bom_product_template_attribute_value_ids.add(self.dashboard_gps_yes)
        bom_dashboard = bom_dashboard.save()

        blue_car_with_gps = self.car._get_variant_for_combination(self.car_color_blue + self.car_gps_yes)

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_car.id, searchQty=1, searchVariant=blue_car_with_gps.id)
        # Two lines. blue dashboard with gps and blue paint.
        self.assertEqual(len(report_values['lines']['components']), 2)

        # 10l of blue paint
        blue_paint = self.paint._get_variant_for_combination(self.paint_color_blue)
        self.assertEqual(blue_paint.id, report_values['lines']['components'][0]['product'].id)
        self.assertEqual(report_values['lines']['components'][0]['quantity'], 10)
        # 1 blue dashboard with GPS
        blue_dashboard_gps = self.dashboard._get_variant_for_combination(self.dashboard_color_blue + self.dashboard_gps_yes)
        self.assertEqual(blue_dashboard_gps.id, report_values['lines']['components'][1]['product'].id)
        self.assertEqual(report_values['lines']['components'][1]['quantity'], 1)
        report_values_dashboad = report_values['lines']['components'][1]

        self.assertEqual(len(report_values_dashboad['components']), 2)
        self.assertEqual(blue_paint.id, report_values_dashboad['components'][0]['product'].id)
        self.assertEqual(self.gps.id, report_values_dashboad['components'][1]['product'].id)

        # 0.5l of paint at price of 20$/litre -> 10$
        self.assertEqual(report_values_dashboad['components'][0]['bom_cost'], 10)
        # GPS 700$
        self.assertEqual(report_values_dashboad['components'][1]['bom_cost'], 700)

        # Dashboard blue with GPS should have a BoM cost of 710$
        self.assertEqual(report_values['lines']['components'][1]['bom_cost'], 710)
        # 10l of paint at price of 20$/litre -> 200$
        self.assertEqual(report_values['lines']['components'][0]['bom_cost'], 200)

        # Total cost of blue car with GPS: 10 + 700 + 200 = 910
        self.assertEqual(report_values['lines']['bom_cost'], 910)

        red_car_without_gps = self.car._get_variant_for_combination(self.car_color_red + self.car_gps_no)

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_car.id, searchQty=1, searchVariant=red_car_without_gps.id)
        # Same math than before but without GPS
        self.assertEqual(report_values['lines']['bom_cost'], 210)

    def test_22_bom_report_recursive_bom(self):
        """ Test report with recursive BoM and different quantities.
        BoM 1:
        product = Finished (units)
        quantity = 100 units
        - Semi-Finished 5 kg

        BoM 2:
        product = Semi-Finished (kg)
        quantity = 11 kg
        - Assembly 2 dozens

        BoM 3:
        product = Assembly (dozens)
        quantity = 5 dozens
        - Raw Material 4 litres (product.product 5$/litre)

        Check the Price for 80 units of Finished -> 2.92$:
        """
        # Create a products templates
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_kg = self.env.ref('uom.product_uom_kgm')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        uom_litre = self.env.ref('uom.product_uom_litre')

        finished = self.env['product.product'].create({
            'name': 'Finished',
            'is_storable': True,
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        semi_finished = self.env['product.product'].create({
            'name': 'Semi-Finished',
            'is_storable': True,
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
        })

        assembly = self.env['product.product'].create({
            'name': 'Assembly',
            'is_storable': True,
            'uom_id': uom_dozen.id,
            'uom_po_id': uom_dozen.id,
        })

        raw_material = self.env['product.product'].create({
            'name': 'Raw Material',
            'is_storable': True,
            'uom_id': uom_litre.id,
            'uom_po_id': uom_litre.id,
            'standard_price': 5,
        })

        #Create bom
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = finished.product_tmpl_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = semi_finished
            line.product_uom_id = uom_kg
            line.product_qty = 5
        bom_finished = bom_finished.save()

        bom_semi_finished = Form(self.env['mrp.bom'])
        bom_semi_finished.product_tmpl_id = semi_finished.product_tmpl_id
        bom_semi_finished.product_qty = 11
        with bom_semi_finished.bom_line_ids.new() as line:
            line.product_id = assembly
            line.product_uom_id = uom_dozen
            line.product_qty = 2
        bom_semi_finished = bom_semi_finished.save()

        bom_assembly = Form(self.env['mrp.bom'])
        bom_assembly.product_tmpl_id = assembly.product_tmpl_id
        bom_assembly.product_qty = 5
        with bom_assembly.bom_line_ids.new() as line:
            line.product_id = raw_material
            line.product_uom_id = uom_litre
            line.product_qty = 4
        bom_assembly = bom_assembly.save()

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_finished.id, searchQty=80)

        self.assertAlmostEqual(report_values['lines']['bom_cost'], 2.92)

    def test_bom_report_capacity_with_quantity_of_0(self):
        target = self.env['product.product'].create({
            'name': 'Target',
            'is_storable': True,
        })

        product_one = self.env['product.product'].create({
            'name': 'Component one',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(product_one, self.stock_location, 3.0)

        product_two = self.env['product.product'].create({
            'name': 'Component two',
            'is_storable': True,
        })
        self.env['stock.quant']._update_available_quantity(product_two, self.stock_location, 4.0)

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': target.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': product_one.id,
                    'product_qty': 0,
                    'product_uom_id': self.uom_unit.id,
                }),
                Command.create({
                    'product_id': product_two.id,
                    'product_qty': 0.1,
                    'product_uom_id': self.uom_unit.id,
                })
            ]
        })

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id)

        # The first product shouldn't affect the producible quantity because the target needs none of it
        # So with 4 of the second product available, we can produce 40 items
        self.assertEqual(report_values["lines"]["producible_qty"], 40)

    def test_bom_report_capacity_with_duplicate_components(self):
        self.env['stock.quant']._update_available_quantity(self.product_2, self.stock_location, 2.0)
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_3.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 2,
                }),
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 2,
                })
            ]
        })

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id)
        # Total quantity of components is 4, so shouldn't be able to produce a single one.
        self.assertEqual(report_values['lines']['producible_qty'], 0)

    def test_bom_report_same_component(self):
        """ Test report bom structure with duplicated components.
        """
        final_product_tmpl = self.env['product.template'].create({'name': 'Final Product', 'is_storable': True})
        component_product = self.env['product.product'].create({'name': 'Compo 1', 'is_storable': True})

        self.env['stock.quant']._update_available_quantity(component_product, self.stock_location, 3.0)

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product_tmpl.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': component_product.id,
                    'product_qty': 3,
                    'product_uom_id': self.uom_unit.id,
                }),
                Command.create({
                    'product_id': component_product.id,
                    'product_qty': 3,
                    'product_uom_id': self.uom_unit.id,
                })
            ]
        })

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id)
        line_values = report_values['lines']['components'][0]
        self.assertEqual(line_values['availability_state'], 'unavailable', 'The merged components should be unavailable')

    def test_report_data_bom_with_0_qty(self):
        """
        Test that a bom with a child-bom set with a zero qty will still have have 0 qty for the child-bom on the report.
        """
        self.bom_4.bom_line_ids = [(0, 0, {
            'product_id': self.bom_2.product_id.id,
            'product_qty': 1.0,
        })]
        self.bom_4.bom_line_ids.product_qty = 0
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=self.bom_4.id, searchQty=1, searchVariant=False)

        self.assertEqual(sum([value['quantity'] for value in report_values['lines']['components'][:2]]), 0, 'The quantity should be set to 0 for all components of the bom.')

    def test_validate_no_bom_line_with_same_product(self):
        """
        Cannot set a BOM line on a BOM with the same product as the BOM itself
        """
        finished = self.env['product.product'].create({
            'name': 'Finished',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'uom_po_id': self.uom_unit.id,
        })
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = finished.product_tmpl_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = finished
            line.product_uom_id = self.uom_unit
            line.product_qty = 5
        with self.assertRaises(exceptions.ValidationError), self.cr.savepoint():
            bom_finished = bom_finished.save()

    def test_validate_no_bom_line_with_same_product_variant(self):
        """
        Cannot set a BOM line on a BOM with the same product variant as the BOM itself
        """
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = self.product_7_template
        bom_finished.product_id = self.product_7_3
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_3
            line.product_uom_id = self.uom_unit
            line.product_qty = 5
        with self.assertRaises(exceptions.ValidationError), self.cr.savepoint():
            bom_finished = bom_finished.save()

    def test_validate_bom_line_with_different_product_variant(self):
        """
        Can set a BOM line on a BOM with a different product variant as the BOM itself (same product)
        Usecase for example A black T-shirt made  from a white T-shirt and
        black color.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = self.product_7_template
        bom_finished.product_id = self.product_7_3
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_2
            line.product_uom_id = uom_unit
            line.product_qty = 5
        bom_finished = bom_finished.save()

    def test_validate_bom_line_with_variant_of_bom_product(self):
        """
        Can set a BOM line on a BOM with a product variant when the BOM has no variant selected
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = self.product_6.product_tmpl_id
        # no product_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_2
            line.product_uom_id = uom_unit
            line.product_qty = 5
        bom_finished = bom_finished.save()

    def test_replenishment(self):
        """ Tests the auto generation of manual orderpoints.
            The multiple quantity of the orderpoint should be the
            quantity of the BoM in the UoM of the product.
        """
        manufacturing_route_id = self.ref('mrp.route_warehouse0_manufacture')

        product_gram = self.env['product.product'].create({
            'name': 'Product sold in grams',
            'is_storable': True,
            'uom_id': self.uom_gm.id,
            'uom_po_id': self.uom_gm.id,
            'route_ids': [(4, manufacturing_route_id)],
        })
        # We create a BoM that manufactures 2kg of product
        self.env['mrp.bom'].create({
            'product_id': product_gram.id,
            'product_tmpl_id': product_gram.product_tmpl_id.id,
            'product_uom_id': self.uom_kg.id,
            'product_qty': 2.0,
            'type': 'normal',
        })
        # We create a delivery order of 2300 grams
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gram
            move.product_uom_qty = 2300.0
        customer_picking = picking_form.save()
        customer_picking.action_confirm()

        # We check the created orderpoint
        self.env.flush_all()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product_gram.id)])
        self.assertEqual(orderpoint.route_id.id, manufacturing_route_id)
        self.assertEqual(orderpoint.qty_multiple, 2000.0)
        self.assertEqual(orderpoint.qty_to_order, 4000.0)

    def test_bom_generated_from_mo(self):
        """ Creates a Manufacturing Order without BoM, then uses it to generate a new BoM.
        Checks the generated BoM has the expected BoM lines, by-products and operations.
        """
        # Creates some products.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Monster in Jar"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Monster"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Jar"))
        by_product = self.env['product.product'].create(dict(common_vals, name="Monster's Tears"))

        def create_mo(qty_to_produce=1):
            # Creates a MO using some components.
            mo_form = Form(self.env['mrp.production'])
            mo_form.product_id = finished_product
            mo_form.product_qty = qty_to_produce
            for component in [component_1, component_2]:
                with mo_form.move_raw_ids.new() as raw_move:
                    raw_move.product_id = component
                    raw_move.product_uom_qty = qty_to_produce
            return mo_form.save()

        def generate_bom_from_mo(mo):
            action_generate_new_bom = mo.action_generate_bom()
            return Form(self.env['mrp.bom'].with_context(action_generate_new_bom['context'])).save()

        # Generates a BoM from a draft MO.
        mo_1 = create_mo()
        bom_from_mo_1 = generate_bom_from_mo(mo_1)
        # Checks the MO's data.
        self.assertEqual(mo_1.bom_id, bom_from_mo_1, "New BoM was assigned to the draft MO")
        self.assertEqual(len(mo_1.move_raw_ids), 2)
        self.assertEqual(mo_1.move_raw_ids[0].bom_line_id, bom_from_mo_1.bom_line_ids[0])
        self.assertEqual(mo_1.move_raw_ids[1].bom_line_id, bom_from_mo_1.bom_line_ids[1])
        # Checks the BoM's data.
        self.assertEqual(bom_from_mo_1.product_id, finished_product)
        self.assertRecordValues(bom_from_mo_1.bom_line_ids, [
            {'product_id': component_1.id, 'product_qty': 1},
            {'product_id': component_2.id, 'product_qty': 1},
        ])
        bom_from_mo_1.active = False  # Archives the created BoM to avoid to use it for the next MOs

        # Generates a BoM from a done MO.
        mo_2 = create_mo()
        mo_2.action_confirm()
        mo_2.button_mark_done()
        move_ids = mo_2.move_raw_ids.ids
        bom_from_mo_2 = generate_bom_from_mo(mo_2)
        bom_lines = bom_from_mo_2.bom_line_ids
        # Checks the MO's data.
        self.assertEqual(mo_2.bom_id, bom_from_mo_2, "New BoM should be assigned to the done MO")
        # The move lines weren't linked to the BoM lines since the MO is done.
        self.assertRecordValues(mo_2.move_raw_ids, [
            {'bom_line_id': False, 'id': move_ids[0], 'product_id': bom_lines[0].product_id.id},
            {'bom_line_id': False, 'id': move_ids[1], 'product_id': bom_lines[1].product_id.id},
        ])
        # Checks the BoM's data.
        self.assertEqual(bom_from_mo_2.product_id, finished_product)
        self.assertRecordValues(bom_from_mo_2.bom_line_ids, [
            {'product_id': component_1.id, 'product_qty': 1},
            {'product_id': component_2.id, 'product_qty': 1},
        ])
        bom_from_mo_2.active = False  # Archives the created BoM to avoid to use it for the next MOs

        # Generates a BoM from a confirmed MO using operations and by-products.
        self._enable_mrp_byproducts(self.user_stock_user) # TODO: sudo?
        # Produces 3 qties to check if the operations' duration will be correctly divided by 3.
        mo_3 = create_mo(3)
        mo_3.action_confirm()
        mo_form = Form(mo_3)
        with mo_form.workorder_ids.new() as operation:
            operation.name = "Kiss the Monster on its Forehead 😘"
            operation.workcenter_id = self.workcenter_1
            operation.duration_expected = 60
        with mo_form.workorder_ids.new() as operation:
            operation.name = "Put the Monster in the Jar!"
            operation.workcenter_id = self.workcenter_2
            operation.duration_expected = 480
        with mo_form.move_byproduct_ids.new() as by_product_line:
            by_product_line.product_id = by_product
            by_product_line.quantity = 6
        mo_3 = mo_form.save()
        bom_from_mo_3 = generate_bom_from_mo(mo_3)
        # Checks the MO's data.
        self.assertEqual(mo_3.bom_id, bom_from_mo_3, "New BoM was assigned to the confirmed MO")
        self.assertEqual(mo_3.move_raw_ids[0].bom_line_id, bom_from_mo_3.bom_line_ids[0])
        self.assertEqual(mo_3.move_raw_ids[1].bom_line_id, bom_from_mo_3.bom_line_ids[1])
        self.assertEqual(mo_3.workorder_ids[0].operation_id, bom_from_mo_3.operation_ids[0])
        self.assertEqual(mo_3.workorder_ids[1].operation_id, bom_from_mo_3.operation_ids[1])
        self.assertEqual(mo_3.move_byproduct_ids.byproduct_id, bom_from_mo_3.byproduct_ids)
        # Checks the BoM's data.
        self.assertEqual(mo_3.bom_id, bom_from_mo_3)
        self.assertEqual(bom_from_mo_3.product_id, finished_product)
        self.assertEqual(bom_from_mo_3.product_qty, 3)
        self.assertRecordValues(bom_from_mo_3.bom_line_ids, [
            {'product_id': component_1.id, 'product_qty': 3},
            {'product_id': component_2.id, 'product_qty': 3},
        ])
        # Durations should be divided by 3 (op1: 60 / 3 = 20; op2: 480 / 3 : 160).
        self.assertRecordValues(bom_from_mo_3.operation_ids, [
            {'name': "Kiss the Monster on its Forehead 😘", 'workcenter_id': self.workcenter_1.id, 'time_cycle': 20},
            {'name': "Put the Monster in the Jar!", 'workcenter_id': self.workcenter_2.id, 'time_cycle': 160},
        ])
        self.assertEqual(bom_from_mo_3.byproduct_ids.product_id, by_product)
        self.assertEqual(bom_from_mo_3.byproduct_ids.product_qty, 6)

    def test_bom_generated_from_mo_with_different_uom(self):
        """ Creates a Manufacturing Order without BoM and using different UoM for its raw moves,
        then to generate a new BoM from this MO.
        Checks the generated BoM has the expected BoM lines UoM and quantity.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        # Creates some products.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="CO² Molecule"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Carbon Molecule"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Oxygen Molecule"))
        # Creates a MO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.product_qty = 1
        mo_form.product_uom_id = uom_dozen
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_1
            raw_move.product_uom_qty = 12
            raw_move.product_uom = uom_unit
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_2
            raw_move.product_uom_qty = 2
            raw_move.product_uom = uom_dozen
        mo = mo_form.save()
        mo.action_confirm()
        # Generates a BoM from the MO and checks its values.
        action_generate_new_bom = mo.action_generate_bom()
        bom_form = Form(self.env['mrp.bom'].with_context(action_generate_new_bom['context']))
        bom_from_mo = bom_form.save()
        self.assertEqual(bom_from_mo.product_uom_id, uom_dozen)
        self.assertEqual(bom_from_mo.product_qty, 1)
        self.assertRecordValues(bom_from_mo.bom_line_ids, [
            {'product_id': component_1.id, 'product_qty': 12, 'product_uom_id': uom_unit.id},
            {'product_id': component_2.id, 'product_qty': 2, 'product_uom_id': uom_dozen.id},
        ])

    def test_bom_generated_from_mo_with_byproducts(self):
        """ Creates a Manufacturing Order without BoM then to generate a new BoM from this MO and
        modifies by-products values.
        """
        self._enable_mrp_byproducts(self.user_stock_user) # TODO: sudo?
        # Creates some products.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Banana Bread"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Banana"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Sugar, Spice and Everything Nice"))
        by_product = self.env['product.product'].create(dict(common_vals, name="Banana Peels"))
        # Creates a MO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = finished_product
        mo_form.product_qty = 1
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_1
            raw_move.product_uom_qty = 1
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_2
            raw_move.product_uom_qty = 1
        with mo_form.move_byproduct_ids.new() as by_product_move:
            by_product_move.product_id = by_product
            by_product_move.product_uom_qty = 1
            by_product_move.cost_share = 50
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.move_byproduct_ids.cost_share, 50)
        # Generates a BoM from the MO and checks its values.
        action_generate_new_bom = mo.action_generate_bom()
        bom_form = Form(self.env['mrp.bom'].with_context(action_generate_new_bom['context']))
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_qty = 3
        with bom_form.byproduct_ids.edit(0) as bom_by_product:
            bom_by_product.product_qty = 3
            bom_by_product.cost_share = 10
        bom_from_mo = bom_form.save()
        self.assertEqual(mo.bom_id, bom_from_mo)
        self.assertEqual(mo.move_raw_ids[0].product_uom_qty, 3)
        self.assertEqual(mo.move_raw_ids[1].product_uom_qty, 1)
        self.assertEqual(mo.move_byproduct_ids.cost_share, 10)
        self.assertEqual(mo.move_byproduct_ids.product_uom_qty, 3)

    def test_bom_kit_with_sub_kit(self):
        p1, p2, p3, p4, p5, p6 = self.make_prods(6)
        prod1, prod2 = self.make_prods(2)
        self.make_bom(p1, p2, p3)
        self.make_bom(p2, p3, p4)
        bom = self.make_bom(p5, p6)
        bom.bom_line_ids[0].product_qty = 0.1
        bom = self.make_bom(prod1, prod2)
        bom.product_qty = 100

        loc = self.stock_location
        self.env["stock.quant"]._update_available_quantity(p3, loc, 10)
        self.env["stock.quant"]._update_available_quantity(p4, loc, 10)
        self.env["stock.quant"]._update_available_quantity(p6, loc, 5.5)
        self.env["stock.quant"]._update_available_quantity(p6, loc, -4.8)
        self.env["stock.quant"]._update_available_quantity(prod2, loc, 5.57)
        self.env["stock.quant"]._update_available_quantity(prod2, loc, -5)

        self.assertEqual(p1.qty_available, 5.0)
        self.assertEqual(p2.qty_available, 10.0)
        self.assertEqual(p3.qty_available, 10.0)
        self.assertEqual(p5.qty_available, 7.0)
        self.assertEqual(prod1.qty_available, 57.0)

    def test_bom_updates_mo(self):
        """ Creates a Manufacturing Order using a BoM, then modifies the BoM.
        Checks the BoM will be marked as updated in the right situation, and checks the "Update BoM"
        action update the MO accordingly to the changes done in the BoM.
        """
        self._enable_mrp_byproducts(self.user_stock_user) # TODO: sudo?
        # Creates a BoM.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Monster in Jar"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Monster"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Jar"))
        component_3 = self.env['product.product'].create(dict(common_vals, name="Bottle"))
        by_product = self.env['product.product'].create(dict(common_vals, name="Monster's Tears"))
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [Command.create({'product_id': p.id, 'product_qty': 1}) for p in [component_1, component_2]],
        })

        # Creates a MO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 10
        mo_1 = mo_form.save()
        self.assertEqual(mo_1.move_raw_ids[0].product_uom_qty, 10)
        self.assertEqual(mo_1.is_outdated_bom, False)
        # Update MO's component quantity.
        mo_form = Form(mo_1)
        with mo_form.move_raw_ids.edit(0) as raw_move:
            raw_move.product_uom_qty = 123
        mo_1 = mo_form.save()
        self.assertEqual(mo_1.move_raw_ids[0].product_uom_qty, 123)
        self.assertEqual(mo_1.is_outdated_bom, False,
            "Making a modification in the MO shouldn't mark the BoM as updated")

        # Now, adds an operation and a by-product in the BoM.
        bom.byproduct_ids = [Command.create({'product_id': by_product.id, 'product_qty': 2})]
        bom_byproduct = bom.byproduct_ids
        bom.operation_ids = [Command.create({
            'name': "Gently insert the Monster in the Jar",
            'workcenter_id': self.workcenter_1.id,
        })]
        operation = bom.operation_ids

        self.assertEqual(mo_1.is_outdated_bom, True,
            "By-Product and Operation were added to the BoM, it should be marked as updated")
        # Call "Update BoM" action, it should reset the MO as defined by the BoM.
        mo_1.action_update_bom()
        self.assertEqual(mo_1.product_qty, 10,
            "MO's quantity should be kept")
        self.assertEqual(mo_1.is_outdated_bom, False,
            "After 'Update BoM' action, MO's BoM should no longer be marked as updated")
        self.assertEqual(mo_1.workorder_ids.operation_id.id, operation.id)
        self.assertEqual(mo_1.move_byproduct_ids.byproduct_id.id, bom_byproduct.id)

        # Now, checks the update works also with confirmed MO.
        mo_1.action_confirm()
        self.assertEqual(mo_1.is_outdated_bom, False,
            "After 'Update BoM' action, MO's BoM should no longer be marked as updated")
        # Updates the BoM again (increase first component quantity).
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_qty += 1
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True,
            "BoM line's quantity was update, the BoM should be marked as updated")
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False,
            "After 'Update BoM' action, MO's BoM should no longer be marked as updated")
        self.assertRecordValues(mo_1.move_raw_ids, [
            {'bom_line_id': bom.bom_line_ids[0].id, 'product_uom_qty': bom.bom_line_ids[0].product_qty * 10},
            {'bom_line_id': bom.bom_line_ids[1].id, 'product_uom_qty': bom.bom_line_ids[1].product_qty * 10},
        ])
        # Updates the BoM again (replace a component by another product).
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.product_id = component_3
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True,
            "A component was changed, BoM should be marked as updated")
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False,
            "There should be no difference between the MO and BoM")
        self.assertRecordValues(mo_1.move_raw_ids, [
            {'bom_line_id': bom.bom_line_ids[0].id, 'product_id': component_1.id},
            {'bom_line_id': bom.bom_line_ids[1].id, 'product_id': component_3.id},
        ])

        # Updates the BoM again (delete a BoM line).
        bom_form = Form(bom)
        bom_form.bom_line_ids.remove(1)
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True,
            "A component was changed, BoM should be marked as updated")
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False,
            "There should be no difference between the MO and BoM")
        self.assertEqual(len(mo_1.move_raw_ids), 1)

        # Updates the BoM again (increase by-product qty).
        with bom_form.byproduct_ids.edit(0) as byproduct_line:
            byproduct_line.product_qty += 1
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True,
            "BoM byproduct's quantity was update, BoM should be marked as updated")
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False,
            "There should be no difference between the MO and BoM")
        self.assertEqual(mo_1.move_byproduct_ids.product_uom_qty, bom.byproduct_ids.product_qty * 10)

        # Updates the BoM by multiplying all its quantities by 3.
        bom.product_qty *= 3
        bom.bom_line_ids[0].product_qty *= 3
        bom.byproduct_ids.product_qty *= 3
        self.assertEqual(mo_1.is_outdated_bom, True,
            "Even if the BoM's changes don't imply actual changes for the MO, it should be marked as updated.")

    def test_bom_updates_mo_with_different_uom(self):
        """ Creates a Manufacturing Order using a BoM and produces 1 dozen of the finished product,
        then modifies the BoM's component's quantity and update the MO.
        Checks the MO's raw moves' quantities are correctly updated.
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        # Creates a BoM.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Monster in Jar"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Monster"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Jar"))
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 2.0,
            'bom_line_ids': [Command.create({'product_id': p.id, 'product_qty': 1}) for p in [component_1, component_2]],
        })

        # Creates a MO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo_form.product_uom_id = uom_dozen
        mo_1 = mo_form.save()
        self.assertRecordValues(mo_1.move_raw_ids, [{
            'product_id': component_1.id, 'product_uom_qty': 24, 'product_uom': uom_unit.id,
        }, {
            'product_id': component_2.id, 'product_uom_qty': 24, 'product_uom': uom_unit.id,
        }])

        ### Test draft MO ###
        # Updates BOM's quantity to 1 unit
        bom.product_qty = 1
        self.assertEqual(mo_1.is_outdated_bom, True,
            "BoM changed, it should be marked as updated.")
        mo_1.action_update_bom()
        self.assertRecordValues(mo_1,
            [{'product_qty': 4, 'product_uom_id': uom_dozen.id}])
        self.assertRecordValues(mo_1.move_raw_ids, [{
            'product_id': component_1.id, 'product_uom_qty': 48, 'product_uom': uom_unit.id,
        }, {
            'product_id': component_2.id, 'product_uom_qty': 48, 'product_uom': uom_unit.id,
        }])

        ### Test confirmed MO ###
        mo_1.product_qty = 1
        self.assertRecordValues(mo_1.move_raw_ids, [{
            'product_id': component_1.id, 'product_uom_qty': 12, 'product_uom': uom_unit.id,
        }, {
            'product_id': component_2.id, 'product_uom_qty': 12, 'product_uom': uom_unit.id,
        }])
        mo_1.action_confirm()
        # Updates the BoM by set the first BoM line's quantity to 2.
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_qty = 2
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)

        # Call "Update BoM" action, it should update the MO raw moves' quantity accordingly.
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False)
        self.assertRecordValues(mo_1.move_raw_ids, [{
            'product_id': component_1.id, 'product_uom_qty': 24, 'product_uom': uom_unit.id,
        }, {
            'product_id': component_2.id, 'product_uom_qty': 12, 'product_uom': uom_unit.id,
        }])

        # Do the same but while changing the raw moves' UoM too.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_uom_id = uom_dozen
        with mo_form.move_raw_ids.edit(0) as move_raw:
            move_raw.product_uom_qty = 2
            move_raw.product_uom = uom_dozen
        with mo_form.move_raw_ids.edit(1) as move_raw:
            move_raw.product_uom_qty = 1
            move_raw.product_uom = uom_dozen
        mo_2 = mo_form.save()
        mo_2.action_confirm()
        self.assertRecordValues(mo_2.move_raw_ids, [
            {'product_id': component_1.id, 'product_uom_qty': 2, 'product_uom': uom_dozen.id},
            {'product_id': component_2.id, 'product_uom_qty': 1, 'product_uom': uom_dozen.id}
        ])

        # Updates the BoM by set the second BoM line's quantity to 2.
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.product_qty = 2
        bom = bom_form.save()
        self.assertEqual(mo_2.is_outdated_bom, True)

        # Call "Update BoM" action, it should update the MO raw moves' quantity accordingly.
        mo_2.action_update_bom()
        self.assertEqual(mo_2.is_outdated_bom, False)
        # As there is a difference for the second component, the quantity should
        # be updated (resets the UoM from the BoM line's one).
        self.assertRecordValues(mo_2.move_raw_ids, [
            {'product_id': component_1.id, 'product_uom_qty': 2, 'product_uom': uom_dozen.id},
            {'product_id': component_2.id, 'product_uom_qty': 24, 'product_uom': uom_unit.id}
        ])

    def test_bom_updates_mo_after_updating_operations(self):
        """ Creates a Manufacturing Order using a BoM with operations and checks the raw moves are
        correctly linked to the right operation/workorder. Then modifies the BoM and updates the MO
        and checks the moves' operation/workorder are correctly updated too.
        """
        # Creates a BoM.
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Monster in Jar"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Monster"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Jar"))
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [Command.create({'product_id': p.id, 'product_qty': 1}) for p in [component_1, component_2]],
            'operation_ids': [
                Command.create({'name': 'OP1', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 10, 'sequence': 1}),
                Command.create({'name': 'OP2', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 2}),
            ],
        })
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0].id
        # Creates a MO and confirms it.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_1 = mo_form.save()
        mo_1.action_confirm()
        self.assertRecordValues(mo_1.move_raw_ids, [
            {'operation_id': bom.operation_ids[0].id, 'workorder_id': mo_1.workorder_ids[0].id},
            {'operation_id': False, 'workorder_id': mo_1.workorder_ids[1].id},
        ])

        # Adds a new operation and links BoM's lines to other operations.
        self.env['mrp.routing.workcenter'].create({
            'name': 'OP3', 'bom_id': bom.id, 'workcenter_id': self.workcenter_1.id
        })
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.operation_id = bom.operation_ids[2]
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.operation_id = bom.operation_ids[0]
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)
        # Updates the MO's BoM, its raw moves' operations/workorders should be updated too.
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False)
        self.assertRecordValues(mo_1.move_raw_ids, [
            {'operation_id': bom.operation_ids[2].id, 'workorder_id': mo_1.workorder_ids[2].id},
            {'operation_id': bom.operation_ids[0].id, 'workorder_id': mo_1.workorder_ids[0].id},
        ])

        # Modifies the BoM's operations again.
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.operation_id = self.env['mrp.routing.workcenter']
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.operation_id = self.env['mrp.routing.workcenter']
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)
        # Updates the MO's BoM, its raw moves' operations/workorders should be correctly linked.
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False)
        self.assertRecordValues(mo_1.move_raw_ids, [
            {'operation_id': False, 'workorder_id': mo_1.workorder_ids[2].id},
            {'operation_id': False, 'workorder_id': mo_1.workorder_ids[2].id},
        ])

    def test_bom_updates_mo_with_pre_prod_picking(self):
        """ With a 2-steps config, creates a MO, then updates its BoM by
        replacing one of its BoM line's product. Updates the MO and checks a new
        move for this product was created in the MO's picking.
        """
        self._enable_adv_location(self.user_stock_user) # TODO: sudo?
        self.warehouse_1.manufacture_steps = 'pbm'

        # Creates a MO.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = self.bom_1
        mo_form.picking_type_id = self.warehouse_1.manu_type_id
        mo_1 = mo_form.save()
        mo_1.action_confirm()
        picking = mo_1.picking_ids
        self.assertRecordValues(picking.move_ids, [
            {'product_id': self.product_2.id, 'product_uom_qty': 2},
            {'product_id': self.product_1.id, 'product_uom_qty': 4},
        ])

        # Updates the BoM, then updates the MO.
        bom_form = Form(self.bom_1)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_id = self.product_3
        bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)
        mo_1.action_update_bom()
        self.assertRecordValues(picking.move_ids, [
            {'product_id': self.product_2.id, 'product_uom_qty': 2},  # Ideally, this move should have been deleted but this isn't handled for now.
            {'product_id': self.product_1.id, 'product_uom_qty': 4},
            {'product_id': self.product_3.id, 'product_uom_qty': 2},
        ])

    def test_operation_blocked_by_another_operation(self):
        """ Test that an operation is not blocked by another operation if the variant is different
            Product with 4 variants (red big, red medium, blue big, blue medium)
            BoM:
                - OP1 (apply on Red)
                - OP2 (blocked by OP1)
            Create a MO for Red big, OP1 is started, OP2 should be blocked
            Create a Mo for Blue big, OP1 is not applied, OP2 should not be blocked
        """
        ProductAttribute = self.env['product.attribute']
        ProductAttributeValue = self.env['product.attribute.value']

        # Product Attribute
        att_color = ProductAttribute.create({'name': 'Color', 'sequence': 1})
        att_size = ProductAttribute.create({'name': 'size', 'sequence': 2})

        # Product Attribute color Value
        att_color_red = ProductAttributeValue.create({'name': 'red', 'attribute_id': att_color.id, 'sequence': 1})
        att_color_blue = ProductAttributeValue.create({'name': 'blue', 'attribute_id': att_color.id, 'sequence': 2})
        # Product Attribute size Value
        att_size_big = ProductAttributeValue.create({'name': 'big', 'attribute_id': att_size.id, 'sequence': 1})
        att_size_medium = ProductAttributeValue.create({'name': 'medium', 'attribute_id': att_size.id, 'sequence': 2})

        # Create create a product with 4 variants
        product_template = self.env['product.template'].create({
            'name': 'Sofa',
            'attribute_line_ids': [
                (0, 0, {
                    'attribute_id': att_color.id,
                    'value_ids': [(6, 0, [att_color_red.id, att_color_blue.id])]
                }),
                (0, 0, {
                    'attribute_id': att_size.id,
                    'value_ids': [(6, 0, [att_size_big.id, att_size_medium.id])]
                })
            ]
        })
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': product_template.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'allow_operation_dependencies': True,
            'operation_ids': [(0, 0, {'name': 'op1', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0, 'bom_product_template_attribute_value_ids': [(4, att_color_blue.pav_attribute_line_ids.product_template_value_ids[0].id)]}),
                                (0, 0, {'name': 'op2', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0})],
        })
        # Make 1st workorder depend on 2nd
        bom.operation_ids[1].blocked_by_operation_ids = [Command.link(bom.operation_ids[0].id)]

        # Make MO for red big
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_template.product_variant_ids[0]
        mo_form.bom_id = bom
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        # Make MO for blue big
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product_template.product_variant_ids[2]
        mo_form.bom_id = bom
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        mo.qty_producing = 1.0
        mo.action_assign()
        mo.button_plan()
        mo.button_mark_done()
        self.assertEqual(mo.state, 'done')

    def test_cycle_on_line_creation(self):
        bom_1_finished_product = self.bom_1.product_id
        bom_2_finished_product = self.bom_2.product_id
        with self.assertRaises(exceptions.ValidationError):
            # finished product is one of the components:
            self.bom_1.bom_line_ids = [(0, 0, {'product_id': bom_1_finished_product.id, 'product_qty': 1.0},)]
        with self.assertRaises(exceptions.ValidationError):
            # cycle:
            self.bom_1.bom_line_ids = [(0, 0, {'product_id': bom_2_finished_product.id, 'product_qty': 1.0},)]

    def test_cycle_on_line_update(self):
        lines = self.bom_1.bom_line_ids
        bom_2_finished_product = self.bom_2.product_id
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.bom_line_ids = [(1, lines[0].id, {'product_id': bom_2_finished_product.id})]

    def test_cycle_on_bom_unarchive(self):
        finished_product = self.bom_1.product_id
        component = self.bom_1.bom_line_ids.product_id[0]
        self.bom_1.active = False
        self.env['mrp.bom'].create({
            'product_id': component.id,
            'product_tmpl_id': component.product_tmpl_id.id,
            'product_uom_id': component.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': finished_product.id, 'product_qty': 1.0}),
            ],
        })
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.active = True

    def test_cycle_on_bom_creation(self):
        finished_product = self.bom_4.product_id
        component = self.bom_4.bom_line_ids.product_id
        with self.assertRaises(exceptions.ValidationError):
            self.env['mrp.bom'].create({
                'product_id': component.id,
                'product_tmpl_id': component.product_tmpl_id.id,
                'product_uom_id': component.uom_id.id,
                'product_qty': 1.0,
                'type': 'normal',
                'bom_line_ids': [
                    (0, 0, {'product_id': finished_product.id, 'product_qty': 1.0}),
                ],
            })

    def test_indirect_cycle_on_bom_creation(self):
        """
        Three BoMs:
            A -> D
            A -> B
            B -> C
        Create a new BoM C -> A. At first glance, this new BoM is ok because it
        does nat have a cycle (C -> A -> D). But there is an indirect cycle:
        A -> B -> C -> A
        Hence this new BoM should raise an error.
        """
        product_A, product_B, product_C, product_D = self.env['product.product'].create([{
            'name': '%s' % i
        } for i in range(4)])
        self.env['mrp.bom'].create([{
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': finished.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': compo.id, 'product_qty': 1.0}),
            ],
        } for finished, compo, in [
            (product_A, product_D),
            (product_A, product_B),
            (product_B, product_C),
        ]])
        with self.assertRaises(exceptions.ValidationError):
            self.env['mrp.bom'].create({
                'product_id': product_C.id,
                'product_tmpl_id': product_C.product_tmpl_id.id,
                'product_uom_id': product_C.uom_id.id,
                'product_qty': 1.0,
                'type': 'normal',
                'bom_line_ids': [
                    (0, 0, {'product_id': product_A.id, 'product_qty': 1.0}),
                ],
            })

    def test_cycle_on_bom_sequencing(self):
        """
        Six BoMs:
            A -> D
            A -> B
            C -> D
            C -> E
            B -> C
            C -> A
        First new sequence: we reverse C->D and C->E, this is ok as it does not
        create any cycle. Change the sequence again and set C->A before C->D: it
        should raise an error because C->A becomes the main BoM of C, and this
        will create a cycle: A -> B -> C -> A
        """
        product_A, product_B, product_C, product_D, product_E = self.env['product.product'].create([{
            'name': '%s' % i
        } for i in range(5)])
        boms = self.env['mrp.bom'].create([{
            'product_id': finished.id,
            'product_tmpl_id': finished.product_tmpl_id.id,
            'product_uom_id': finished.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': compo.id, 'product_qty': 1.0}),
            ],
        } for finished, compo, in [
            (product_A, product_D),
            (product_A, product_B),
            (product_C, product_D),
            (product_C, product_E),
            (product_B, product_C),
            (product_C, product_A),
        ]])

        # simulate resequence from UI (reverse C->D and C->E)
        # (see odoo/addons/web/controllers/main.py:1352)
        boms.invalidate_recordset()
        for i, record in enumerate(boms[0] | boms[1] | boms[3] | boms[2] | boms[4] | boms[5]):
            record.write({'sequence': i})

        # simulate a second resequencing (set C->A before C->D)
        with self.assertRaises(exceptions.ValidationError):
            for i, record in enumerate(boms[0] | boms[1] | boms[5] | boms[3] | boms[2] | boms[4]):
                record.write({'sequence': i})

    def test_cycle_on_legit_apply_variants(self):
        """ Should not raise anything """
        self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.product_7_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_1.id,
                    'product_qty': 1.0
                }),
                (0, 0, {
                    'product_id': self.product_2.id,
                    'product_qty': 1.0,
                    'bom_product_template_attribute_value_ids': [(4, self.product_7_attr1_v2.id)]
                }),
            ],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_2.product_tmpl_id.id,
            'product_uom_id': self.product_2.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': self.product_7_1.id, 'product_qty': 1.0}),
            ],
        })

    def test_component_when_bom_change(self):
        """
        Checks that the component of the previous BoM is removed when another BoM is set on the MO:
            - Create a product with 2 BoMs:
                BoM 1: compoennt 1
                BoM 2: component 2
            - Create a MO for the product with BoM 1
            - check that the component 1 is set
            - change the BoM on the MO to BoM 2
            - come back to BoM 1
            - check that the component 2 is removed and replaced by the component 1
        """
        # Create BoM 1 with component 1
        bom_1 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.product_7_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({
                'product_id': self.product_1.id,
                'product_qty': 1.0,
            })],
        })
        # Create BoM 2 with component 2
        bom_2 = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_7_template.id,
            'product_uom_id': self.product_7_template.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [Command.create({
                'product_id': self.product_2.id,
                'product_qty': 1.0,
            })],
        })
        # Create a MO with BoM 1
        mo = self.env['mrp.production'].create({
            'product_qty': 1.0,
            'bom_id': bom_1.id,
        })
        # Check that component 1 is set
        self.assertEqual(mo.move_raw_ids.product_id, self.product_1)
        # Change BoM in the MO to BoM 2
        mo_form = Form(mo)
        mo_form.bom_id = bom_2
        # Check that component 2 is set
        self.assertEqual(mo_form.move_raw_ids._records[0]['product_id'], self.product_2.id)
        self.assertEqual(len(mo_form.move_raw_ids._records), 1)
        # Revert back to BoM 1
        mo_form.bom_id = bom_1
        # Check that component 1 is set again and component 2 is removed
        self.assertEqual(mo_form.move_raw_ids._records[0]['product_id'], self.product_1.id)
        self.assertEqual(len(mo_form.move_raw_ids._records), 1)

    def test_update_operations(self):
        """Update the operations in BoM which reflects the changes in Manufacturing Order"""

        mo_form = Form(self.env['mrp.production'].with_user(self.user_mrp_user))
        mo_form.product_id = self.product_7_1
        mo_form.product_qty = 1.0
        mo_form.bom_id = self.bom_2
        mo = mo_form.save()
        mo.action_confirm()

        self.bom_2.operation_ids.write({
            'name': 'Painting',
            'workcenter_id': self.workcenter_2.id
        })
        self.assertTrue(mo.is_outdated_bom)

        mo.action_update_bom()
        self.assertEqual(self.bom_2.operation_ids.name, mo.workorder_ids.name)
        self.assertEqual(self.bom_2.operation_ids.workcenter_id, mo.workorder_ids.workcenter_id)

    def test_archive_operations(self):
        """Archive the operation in BoM and update the BoM in MO
        Unarchive the operation which will reflect in BoM and MO"""

        mo_form = Form(self.env['mrp.production'].with_user(self.user_mrp_user))

        mo_form.product_id = self.product_7_1
        mo_form.product_qty = 1.0
        mo_form.bom_id = self.bom_2
        mo_order = mo_form.save()
        mo_order.action_confirm()

        operation_ids = self.bom_2.operation_ids.ids
        self.bom_2.operation_ids.action_archive()
        self.assertTrue(mo_order.is_outdated_bom)

        mo_order.action_update_bom()
        self.assertEqual(len(mo_order.workorder_ids), 0)

        self.env['mrp.routing.workcenter'].browse(operation_ids).action_unarchive()
        self.assertTrue(mo_order.is_outdated_bom)
        mo_order.action_update_bom()
        self.assertEqual(len(mo_order.workorder_ids), 1)

    def test_availability_bom_type_kit(self):
        """ Product should only be available if bom type is kit """
        product_one = self.env['product.product'].create({
            'name': 'Product',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        product_two = self.env['product.product'].create({
            'name': 'Component',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
        })
        self.env['stock.quant']._update_available_quantity(product_two, self.stock_location, 4.0)

        bom_normal = self.env['mrp.bom'].create({
            'product_tmpl_id': product_one.product_tmpl_id.id,
            'product_uom_id': product_one.product_tmpl_id.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': product_two.id,
                    'product_qty': 1,
                }),
            ]
        })
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_normal.id)
        line_values = report_values['lines']
        self.assertEqual(line_values['availability_state'], 'unavailable')

        bom_kit = self.env['mrp.bom'].create({
            'product_tmpl_id': product_one.product_tmpl_id.id,
            'product_uom_id': product_one.product_tmpl_id.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': product_two.id,
                    'product_qty': 1,
                }),
            ]
        })
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_kit.id)
        line_values = report_values['lines']
        self.assertEqual(line_values['availability_state'], 'available')

    def test_update_bom_in_routing_workcenter(self):
        """
        This test checks the behaviour of updating the BoM associated with a routing workcenter,
        It verifies that the link between the BOM lines and the operation is correctly deleted.
        """
        resource_calendar_std_id = self.env.ref('resource.resource_calendar_std').id
        mrp_workcenter_1 = self.env['mrp.workcenter'].create({
            'name': 'Drill Station 1',
            'resource_calendar_id': resource_calendar_std_id,
        })
        p1, c1, c2, byproduct = self.make_prods(4)
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': p1.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                Command.create({'product_id': c1.id, 'product_qty': 1.0}),
                Command.create({'product_id': c2.id, 'product_qty': 1.0})
                ],
            'byproduct_ids': [
                Command.create({
                    'product_id': byproduct.id, 'product_uom_id': byproduct.uom_id.id, 'product_qty': 1.0,
                })]
        })
        operation_1, operation_2 = self.env['mrp.routing.workcenter'].create([
            {
                'name': 'Operation 1',
                'workcenter_id': mrp_workcenter_1.id,
                'bom_id': bom.id,
            },
            {
                'name': 'Operation 2',
                'workcenter_id': mrp_workcenter_1.id,
                'bom_id': bom.id,
            }
        ])
        bom.bom_line_ids.operation_id = operation_1
        bom.byproduct_ids.operation_id = operation_1
        operation_2.blocked_by_operation_ids = operation_1
        self.assertEqual(operation_1.bom_id, bom)
        operation_1.bom_id = self.bom_1
        self.assertEqual(operation_1.bom_id, self.bom_1)
        self.assertFalse(bom.bom_line_ids.operation_id)
        self.assertFalse(bom.byproduct_ids.operation_id)
        self.assertFalse(operation_2.blocked_by_operation_ids)

    def test_bom_document(self):
        doc_product_bom = self.env['product.document'].create({
            'name': 'doc_product_bom',
            'attached_on_mrp': 'bom',
            'res_id': self.product_4.id,
            'res_model': 'product.product',
        })

        # ensures that the archived docs are not taken into account
        self.env['product.document'].create({
            'name': 'doc_product_bom_archived',
            'active': False,
            'attached_on_mrp': 'bom',
            'res_id': self.product_4.id,
            'res_model': 'product.product',
        })

        doc_template_bom = self.env['product.document'].create({
            'name': 'doc_template_bom',
            'attached_on_mrp': 'bom',
            'res_id': self.product_4.product_tmpl_id.id,
            'res_model': 'product.template',
        })

        attachments = doc_template_bom.ir_attachment_id + doc_product_bom.ir_attachment_id

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_4.product_tmpl_id.id,
            'product_uom_id': self.product_4.product_tmpl_id.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
        })

        # only the document linked to the product.template and visible at bom should be in the chatter
        self.assertEqual(bom._get_extra_attachments(), doc_template_bom.ir_attachment_id)

        bom.product_id = self.product_4
        # the document linked to the product.template and product.product visible at bom should be in the chatter
        self.assertEqual(bom._get_extra_attachments(), attachments)

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_5.product_tmpl_id.id,
            'product_uom_id': self.product_5.product_tmpl_id.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_4.id,
                    'product_qty': 1,
                }),
            ]
        })

        self.assertEqual(bom.bom_line_ids.attachments_count, 2)
        action = bom.bom_line_ids.action_see_attachments()
        # the filter is applied because there are attachements on the product.product
        self.assertTrue(action['context']['search_default_context_variant'])

        doc_product_bom.attached_on_mrp = 'hidden'
        action = bom.bom_line_ids.action_see_attachments()
        # the filter is not applied because there are attachements on the product.template but not on the product.product
        self.assertFalse(action['context']['search_default_context_variant'])

        doc_template_bom.attached_on_mrp = 'hidden'
        action = bom.bom_line_ids.action_see_attachments()
        # the filter is applied because there are attachements on the product.template and on the product.product
        self.assertTrue(action['context']['search_default_context_variant'])

    def test_compute_days_to_prepare_from_mo_if_unavailable(self):
        """
        Checks that a notification is sent when at least one component can not be resupplied.
        """
        bom = self.bom_1
        product = bom.product_id
        manufacturing_route_id = self.ref('mrp.route_warehouse0_manufacture')
        product.route_ids = [Command.set([manufacturing_route_id])]
        notification = bom.action_compute_bom_days()
        self.assertEqual(bom.days_to_prepare_mo, 0.0)
        self.assertEqual((notification['type'], notification['tag']), ('ir.actions.client', 'display_notification'))

    def test_bom_never_attribute(self):
        # We create 4 bom lines, one without any attribute values, two with one value and one with two values
        # Create a MO with, modify its never_product_template_attribute_value_ids and check if the moves created are correct

        product_attribute_radio = self.env['product.attribute'].create({
            'name': 'PA',
            'display_type': 'radio',
            'create_variant': 'no_variant',
        })
        product = self.env['product.product'].create({
            'name': 'test1',
        })
        self.env['product.attribute.value'].create([{
            'name': 'radio_PAV' + str(i),
            'attribute_id': product_attribute_radio.id
        } for i in range(3)])

        tmpl_attr_line_radio = self.env['product.template.attribute.line'].create({
            'attribute_id': product_attribute_radio.id,
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'value_ids': [(6, 0, product_attribute_radio.value_ids.ids)],
        })

        self.env['mrp.bom'].create({
            'product_tmpl_id': self.product_1.product_tmpl_id.id,
            'product_uom_id': self.product_1.product_tmpl_id.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': self.product_2.id,
                    'product_qty': 1,
                }),
                Command.create({
                    'product_id': self.product_3.id,
                    'product_qty': 2,
                    'bom_product_template_attribute_value_ids': [Command.link(tmpl_attr_line_radio.product_template_value_ids[0].id)]
                }),
                Command.create({
                    'product_id': product.id,
                    'product_qty': 1,
                    'bom_product_template_attribute_value_ids': [Command.link(tmpl_attr_line_radio.product_template_value_ids[1].id)]
                }),
                Command.create({
                    'product_id': self.product_8.id,
                    'product_qty': 10,
                    'bom_product_template_attribute_value_ids': [Command.link(tmpl_attr_line_radio.product_template_value_ids[1].id), Command.link(tmpl_attr_line_radio.product_template_value_ids[2].id)]
                }),
            ]
        })

        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_order = mo_form.save()

        # no never values, so only the first bom line should be used
        self.assertEqual(len(mo_order.move_raw_ids), 1, "Only one move with no never_product_template_attribute_value_ids should be created")
        self.assertEqual(mo_order.move_raw_ids.product_id, self.product_2)

        # one never values, the two first bom line should match
        mo_order.never_product_template_attribute_value_ids = tmpl_attr_line_radio.product_template_value_ids[0]
        self.assertEqual(len(mo_order.move_raw_ids), 2)
        self.assertEqual(mo_order.move_raw_ids.product_id, self.product_2 + self.product_3)

        # two never values, the first and fourth bom line should match
        mo_order.never_product_template_attribute_value_ids = tmpl_attr_line_radio.product_template_value_ids[1] + tmpl_attr_line_radio.product_template_value_ids[2]
        self.assertEqual(len(mo_order.move_raw_ids), 3)
        self.assertEqual(mo_order.move_raw_ids.product_id, self.product_2 + product + self.product_8)

    def test_workorders_on_bom_changes(self):
        """
        Check that the workorders of the MO are changed according to the bom
        and that bom free workorders are not reset on bom changes.
        """
        product = self.product_4
        bom_1, bom_2, bom_3 = self.env['mrp.bom'].create([
            {
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_qty': 1.0,
                'operation_ids': [
                    Command.create({'name': 'op1', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0}),
                    Command.create({'name': 'op2', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0}),
                ],
            },
            {
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_qty': 1.0,
                'operation_ids': [
                    Command.create({'name': 'op3', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0}),
                    Command.create({'name': 'op4', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0}),
                ],
            },
            {
                'product_tmpl_id': product.product_tmpl_id.id,
                'product_qty': 1.0,
                'operation_ids': [
                    Command.create({'name': 'op5', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0}),
                    Command.create({'name': 'op6', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 1.0}),
                ],
            },
        ])
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = product
        mo_form.product_qty = 1.0
        mo_form.bom_id = bom_1
        mo = mo_form.save()
        self.assertEqual(mo.workorder_ids.mapped('name'), ['op1', 'op2'])
        # test simple on change
        with Form(mo) as mo_form:
            mo_form.bom_id = bom_2
        self.assertEqual(mo.workorder_ids.mapped('name'), ['op3', 'op4'])
        # test double onchange
        with Form(mo) as mo_form:
            mo_form.bom_id = bom_1
            mo_form.bom_id = bom_3
        self.assertEqual(mo.workorder_ids.mapped('name'), ['op5', 'op6'])
        # add a new operation and check that it is not removed on bom change
        with Form(mo) as mo_form:
            with mo_form.workorder_ids.new() as wo_form:
                wo_form.name = 'new op'
                wo_form.workcenter_id = self.workcenter_2
        self.assertEqual(mo.workorder_ids.mapped('name'), ['op5', 'op6', 'new op'])
        with Form(mo) as mo_form:
            mo_form.bom_id = bom_2
        self.assertEqual(set(mo.workorder_ids.mapped('name')), {'op3', 'op4', 'new op'})

    def test_manual_consumption_bom_line(self):
        """
        1. Create a BOM with two lines
        2. Attach an operation to the first BOM line
        3. Create an MO
        4. Check that the move with BOM line attached will be treated as a manual consumption move despite the BOM line being automatic consumption
        """
        common_vals = {'is_storable': True}
        finished_product = self.env['product.product'].create(dict(common_vals, name="Monster in Jar"))
        component_1 = self.env['product.product'].create(dict(common_vals, name="Monster"))
        component_2 = self.env['product.product'].create(dict(common_vals, name="Jar"))
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': finished_product.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [Command.create({'product_id': p.id, 'product_qty': 1}) for p in [component_1, component_2]],
            'operation_ids': [
                Command.create({'name': 'OP1', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 10, 'sequence': 1}),
                Command.create({'name': 'OP2', 'workcenter_id': self.workcenter_1.id, 'time_cycle': 15, 'sequence': 2}),
            ],
        })
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0].id
        # Creates a MO and confirms it.
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_1 = mo_form.save()
        mo_1.action_confirm()

        move_with_bom_line_op = mo_1.all_move_raw_ids[0]
        move_without_bom_line_op = mo_1.all_move_raw_ids[1]

        self.assertTrue(move_with_bom_line_op._is_manual_consumption())
        self.assertFalse(move_without_bom_line_op._is_manual_consumption())

    def test_archive_operation(self):
        """ Checks that archiving an operation having both a bom line and a byproduct line linked to it properly unlinks them.
        """
        final, comp1, comp2, bp1, bp2 = self.make_prods(5)
        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final.product_tmpl_id.id,
            'product_qty': 1.0,
            'bom_line_ids': [
                Command.create({'product_id': comp1.id, 'product_qty': 1.0}),
                Command.create({'product_id': comp2.id, 'product_qty': 1.0}),
            ],
            'byproduct_ids': [
                Command.create({'product_id': bp1.id, 'product_qty': 1.0}),
                Command.create({'product_id': bp2.id, 'product_qty': 1.0}),
            ],
            'operation_ids': [
                Command.create({'name': 'OPE_1', 'workcenter_id': self.workcenter_1.id}),
                Command.create({'name': 'OPE_2', 'workcenter_id': self.workcenter_1.id}),
            ],
        })
        # Assign operation to each bom/byproduct line
        ope_1, ope_2 = bom.operation_ids
        bom.bom_line_ids[0].operation_id = ope_1
        bom.byproduct_ids[0].operation_id = ope_1
        bom.bom_line_ids[1].operation_id = ope_2
        bom.byproduct_ids[1].operation_id = ope_2

        # Archive first operation
        ope_1.action_archive()
        self.assertFalse(bom.bom_line_ids[0].operation_id)
        self.assertFalse(bom.byproduct_ids[0].operation_id)
        self.assertEqual(bom.bom_line_ids[1].operation_id, ope_2)
        self.assertEqual(bom.byproduct_ids[1].operation_id, ope_2)


@tagged('-at_install', 'post_install')
class TestTourBoM(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'test1',
            'is_storable': True,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product.id,
            'product_tmpl_id': cls.product.product_tmpl_id.id,
            'product_qty': 1,
            'type': 'normal',
        })
    
    def test_mrp_bom_product_catalog(self):

        self.assertEqual(len(self.bom.bom_line_ids), 0)

        url = f'/odoo/action-mrp.mrp_bom_form_action/{self.bom.id}'

        self.start_tour(url, 'test_mrp_bom_product_catalog', login='admin')
        self.assertEqual(len(self.bom.bom_line_ids), 1)

    def test_manufacture_from_bom(self):
        """
        Create a new MO by pressing the "Manufacture" button in BoM Overview
        """
        url = '/odoo/action-mrp.mrp_bom_form_action'
        self.start_tour(url, 'test_manufacture_from_bom', login='admin', timeout=100)
