# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions, Command, fields
from odoo.tests import Form
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tools import float_compare, float_round, float_repr

from freezegun import freeze_time


@freeze_time(fields.Date.today())
class TestBoM(TestMrpCommon):

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
        tmp_picking_type = self.env['stock.picking.type'].create({
            'name': 'Manufacturing',
            'code': 'mrp_operation',
            'sequence_code': 'TMP',
            'sequence_id': self.env['ir.sequence'].create({
                'code': 'mrp.production',
                'name': 'tmp_production_sequence',
            }).id,
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
        location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(self.product_2, location, 4.0)
        self.env['stock.quant']._update_available_quantity(self.product_3, location, 8.0)
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
        uom_dozens = self.env.ref('uom.product_uom_dozen')
        uom_unit = self.env.ref('uom.product_uom_unit')
        product_unit = self.env['product.product'].create({
            'name': 'Test units',
            'type': 'product',
            'uom_id': uom_unit.id,
        })
        product_dozens = self.env['product.product'].create({
            'name': 'Test dozens',
            'type': 'product',
            'uom_id': uom_dozens.id,
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
                    'product_uom_id': uom_unit.id,
                })
            ]
        })
        location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(product_dozens, location, 1.0)
        self.assertEqual(product_unit.qty_available, 12.0)

    def test_13_negative_on_hand_qty(self):
        # We set the Product Unit of Measure digits to 5.
        # Because float_round(-384.0, 5) = -384.00000000000006
        # And float_round(-384.0, 2) = -384.0
        precision = self.env.ref('product.decimal_product_uom')
        precision.digits = 5

        # We set the Unit(s) rounding to 0.0001 (digit = 4)
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_unit.rounding = 0.0001

        _ = self.env['mrp.bom'].create({
            'product_id': self.product_2.id,
            'product_tmpl_id': self.product_2.product_tmpl_id.id,
            'product_uom_id': uom_unit.id,
            'product_qty': 1.00,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {
                    'product_id': self.product_3.id,
                    'product_qty': 1.000,
                }),
            ]
        })

        self.env['stock.quant']._update_available_quantity(self.product_3, self.env.ref('stock.stock_location_stock'), -384.0)

        kit_product_qty = self.product_2.qty_available  # Without product_3 in the prefetch
        # Use the float_repr to remove extra small decimal (and represent the front-end behavior)
        self.assertEqual(float_repr(float_round(kit_product_qty, precision_digits=precision.digits), precision_digits=precision.digits), '-384.00000')

        self.product_2.invalidate_recordset(['qty_available'])
        kit_product_qty, _ = (self.product_2 + self.product_3).mapped("qty_available")  # With product_3 in the prefetch
        self.assertEqual(float_repr(float_round(kit_product_qty, precision_digits=precision.digits), precision_digits=precision.digits), '-384.00000')

    def test_13_bom_kit_qty_multi_uom(self):
        uom_dozens = self.env.ref('uom.product_uom_dozen')
        uom_unit = self.env.ref('uom.product_uom_unit')
        product_unit = self.env['product.product'].create({
            'name': 'Test units',
            'type': 'product',
            'uom_id': uom_unit.id,
        })
        product_dozens = self.env['product.product'].create({
            'name': 'Test dozens',
            'type': 'product',
            'uom_id': uom_dozens.id,
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
                    'product_uom_id': uom_unit.id,
                })
            ]
        })
        location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(product_dozens, location, 1.0)
        self.assertEqual(product_unit.qty_available, 12.0)

    def test_20_bom_report(self):
        """ Simulate a crumble receipt with mrp and open the bom structure
        report and check that data insde are correct.
        """
        uom_kg = self.env.ref('uom.product_uom_kgm')
        uom_litre = self.env.ref('uom.product_uom_litre')
        crumble = self.env['product.product'].create({
            'name': 'Crumble',
            'type': 'product',
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
        })
        butter = self.env['product.product'].create({
            'name': 'Butter',
            'type': 'product',
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
            'standard_price': 7.01
        })
        biscuit = self.env['product.product'].create({
            'name': 'Biscuit',
            'type': 'product',
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

        # Required to display `operation_ids` in the form view
        self.env.user.groups_id += self.env.ref("mrp.group_mrp_routings")
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
                operation.bom_id = bom_crumble  # Can't handle by the testing env
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Prepare butter'
                operation.time_cycle_manual = 3
                operation.bom_id = bom_crumble
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Mix manually'
                operation.time_cycle_manual = 5
                operation.bom_id = bom_crumble

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
            'type': 'product',
        })
        cream = self.env['product.product'].create({
            'name': 'cream',
            'type': 'product',
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
            'time_start': 2,
            'time_stop': 1,
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
                operation.bom_id = bom_cheese_cake
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter_2
                operation.name = 'Cake mounting'
                operation.time_cycle_manual = 5
                operation.bom_id = bom_cheese_cake

        # TEST CHEESE BOM STRUCTURE VALUE WITH BOM QUANTITY
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_cheese_cake.id, searchQty=60, searchVariant=False)
        #Operation time = 15 min * 60 + time_start + time_stop + capacity_time_start + capacity_time_stop= 928
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
            'type': 'product',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })
        screw = self.env['product.product'].create({
            'name': 'screw',
            'type': 'product',
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

        # Required to display `operation_ids` in the form view
        self.env.user.groups_id += self.env.ref("mrp.group_mrp_routings")
        with Form(bom_drawer) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = screw
                line.product_uom_id = uom_unit
                line.product_qty = 5
            with bom.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Screw drawer'
                operation.time_cycle_manual = 5
                operation.bom_id = bom_drawer

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
            'type': 'product',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })

        semi_finished = self.env['product.product'].create({
            'name': 'Semi-Finished',
            'type': 'product',
            'uom_id': uom_kg.id,
            'uom_po_id': uom_kg.id,
        })

        assembly = self.env['product.product'].create({
            'name': 'Assembly',
            'type': 'product',
            'uom_id': uom_dozen.id,
            'uom_po_id': uom_dozen.id,
        })

        raw_material = self.env['product.product'].create({
            'name': 'Raw Material',
            'type': 'product',
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
        uom_unit = self.env.ref('uom.product_uom_unit')
        location = self.env.ref('stock.stock_location_stock')

        target = self.env['product.product'].create({
            'name': 'Target',
            'type': 'product',
        })

        product_one = self.env['product.product'].create({
            'name': 'Component one',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product_one, location, 3.0)

        product_two = self.env['product.product'].create({
            'name': 'Component two',
            'type': 'product',
        })
        self.env['stock.quant']._update_available_quantity(product_two, location, 4.0)

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': target.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': product_one.id,
                    'product_qty': 0,
                    'product_uom_id': uom_unit.id,
                }),
                Command.create({
                    'product_id': product_two.id,
                    'product_qty': 1,
                    'product_uom_id': uom_unit.id,
                })
            ]
        })

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id)

        # The first product shouldn't affect the producible quantity because the target needs none of it
        # So with 4 of the second product available, we can produce 4 items
        self.assertEqual(report_values["lines"]["producible_qty"], 4)

    def test_bom_report_capacity_with_duplicate_components(self):
        location = self.env.ref('stock.stock_location_stock')
        self.env['stock.quant']._update_available_quantity(self.product_2, location, 2.0)
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
        location = self.env.ref('stock.stock_location_stock')
        uom_unit = self.env.ref('uom.product_uom_unit')
        final_product_tmpl = self.env['product.template'].create({'name': 'Final Product', 'type': 'product'})
        component_product = self.env['product.product'].create({'name': 'Compo 1', 'type': 'product'})

        self.env['stock.quant']._update_available_quantity(component_product, location, 3.0)

        bom = self.env['mrp.bom'].create({
            'product_tmpl_id': final_product_tmpl.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': component_product.id,
                    'product_qty': 3,
                    'product_uom_id': uom_unit.id,
                }),
                Command.create({
                    'product_id': component_product.id,
                    'product_qty': 3,
                    'product_uom_id': uom_unit.id,
                })
            ]
        })

        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom.id)
        line1_values = report_values['lines']['components'][0]
        line2_values = report_values['lines']['components'][1]
        self.assertEqual(line1_values['availability_state'], 'available', 'The first component should be available.')
        self.assertEqual(line2_values['availability_state'], 'unavailable', 'The second component should be marked as unavailable')

    def test_validate_no_bom_line_with_same_product(self):
        """
        Cannot set a BOM line on a BOM with the same product as the BOM itself
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        finished = self.env['product.product'].create({
            'name': 'Finished',
            'type': 'product',
            'uom_id': uom_unit.id,
            'uom_po_id': uom_unit.id,
        })
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = finished.product_tmpl_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = finished
            line.product_uom_id = uom_unit
            line.product_qty = 5
        with self.assertRaises(exceptions.ValidationError), self.cr.savepoint():
            bom_finished = bom_finished.save()

    def test_validate_no_bom_line_with_same_product_variant(self):
        """
        Cannot set a BOM line on a BOM with the same product variant as the BOM itself
        """
        uom_unit = self.env.ref('uom.product_uom_unit')
        bom_finished = Form(self.env['mrp.bom'])
        bom_finished.product_tmpl_id = self.product_7_template
        bom_finished.product_id = self.product_7_3
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_3
            line.product_uom_id = uom_unit
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

        uom_kg = self.env.ref('uom.product_uom_kgm')
        uom_gram = self.env.ref('uom.product_uom_gram')

        product_gram = self.env['product.product'].create({
            'name': 'Product sold in grams',
            'type': 'product',
            'uom_id': uom_gram.id,
            'uom_po_id': uom_gram.id,
        })
        # We create a BoM that manufactures 2kg of product
        self.env['mrp.bom'].create({
            'product_id': product_gram.id,
            'product_tmpl_id': product_gram.product_tmpl_id.id,
            'product_uom_id': uom_kg.id,
            'product_qty': 2.0,
            'type': 'normal',
        })
        # We create a delivery order of 2300 grams
        picking_form = Form(self.env['stock.picking'])
        picking_form.picking_type_id = self.env.ref('stock.picking_type_out')
        with picking_form.move_ids_without_package.new() as move:
            move.product_id = product_gram
            move.product_uom_qty = 2300.0
        customer_picking = picking_form.save()
        customer_picking.action_confirm()

        # We check the created orderpoint
        self.env.flush_all()
        self.env['stock.warehouse.orderpoint']._get_orderpoint_action()
        orderpoint = self.env['stock.warehouse.orderpoint'].search([('product_id', '=', product_gram.id)])
        manufacturing_route_id = self.ref('mrp.route_warehouse0_manufacture')
        self.assertEqual(orderpoint.route_id.id, manufacturing_route_id)
        self.assertEqual(orderpoint.qty_multiple, 2000.0)
        self.assertEqual(orderpoint.qty_to_order, 4000.0)

    def test_bom_kit_with_sub_kit(self):
        p1, p2, p3, p4 = self.make_prods(4)
        self.make_bom(p1, p2, p3)
        self.make_bom(p2, p3, p4)

        loc = self.env.ref("stock.stock_location_stock")
        self.env["stock.quant"]._update_available_quantity(p3, loc, 10)
        self.env["stock.quant"]._update_available_quantity(p4, loc, 10)
        self.assertEqual(p1.qty_available, 5.0)
        self.assertEqual(p2.qty_available, 10.0)
        self.assertEqual(p3.qty_available, 10.0)

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
