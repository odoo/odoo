# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import exceptions
from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.tests import Form
from odoo.tools import float_compare, float_round


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

    def test_bom_report(self):
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

        with Form(bom_crumble) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = butter
                line.product_uom_id = uom_kg
                line.product_qty = 5
            with bom.bom_line_ids.new() as line:
                line.product_id = biscuit
                line.product_uom_id = uom_kg
                line.product_qty = 6

        workcenter = self.env['mrp.workcenter'].create({
            'costs_hour': 10,
            'name': 'Deserts Table'
        })

        routing_form = Form(self.env['mrp.routing'])
        routing_form.name = "Crumble process"
        routing_crumble = routing_form.save()

        with Form(routing_crumble) as routing:
            with routing.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Prepare biscuits'
                operation.time_cycle_manual = 5
            with routing.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Prepare butter'
                operation.time_cycle_manual = 3
            with routing.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Mix manually'
                operation.time_cycle_manual = 5

        bom_crumble.routing_id = routing_crumble.id

        # TEST BOM STRUCTURE VALUE WITH BOM QUANTITY
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=11, searchVariant=False)
        # 5 min 'Prepare biscuits' + 3 min 'Prepare butter' + 5 min 'Mix manually' = 13 minutes
        self.assertEqual(report_values['lines']['operations_time'], 13.0, 'Operation time should be the same for 1 unit or for the batch')
        # Operation cost is the sum of operation line.
        operation_cost = float_round(5 / 60 * 10, precision_digits=2) * 2 + float_round(3 / 60 * 10, precision_digits=2)
        self.assertEqual(float_compare(report_values['lines']['operations_cost'], operation_cost, precision_digits=2), 0, '13 minute for 10$/hours -> 2.16')

        for component_line in report_values['lines']['components']:
            # standard price * bom line quantity * current quantity / bom finished product quantity
            if component_line['prod_id'] == butter.id:
                # 5 kg of butter at 7.01$ for 11kg of crumble -> 35.05$
                self.assertEqual(float_compare(component_line['total'], (7.01 * 5), precision_digits=2), 0)
            if component_line['prod_id'] == biscuit.id:
                # 6 kg of biscuits at 1.50$ for 11kg of crumble -> 9$
                self.assertEqual(float_compare(component_line['total'], (1.5 * 6), precision_digits=2), 0)
        # total price = 35.05 + 9 + operation_cost(0.83 + 0.83 + 0.5 = 2.16) = 46,21
        self.assertEqual(float_compare(report_values['lines']['total'], 46.21, precision_digits=2), 0, 'Product Bom Price is not correct')
        self.assertEqual(float_compare(report_values['lines']['total'] / 11.0, 4.20, precision_digits=2), 0, 'Product Unit Bom Price is not correct')

        # TEST BOM STRUCTURE VALUE BY UNIT
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=1, searchVariant=False)
        # 5 min 'Prepare biscuits' + 3 min 'Prepare butter' + 5 min 'Mix manually' = 13 minutes
        self.assertEqual(report_values['lines']['operations_time'], 13.0, 'Operation time should be the same for 1 unit or for the batch')
        # Operation cost is the sum of operation line.
        operation_cost = float_round(5 / 60 * 10, precision_digits=2) * 2 + float_round(3 / 60 * 10, precision_digits=2)
        self.assertEqual(float_compare(report_values['lines']['operations_cost'], operation_cost, precision_digits=2), 0, '13 minute for 10$/hours -> 2.16')

        for component_line in report_values['lines']['components']:
            # standard price * bom line quantity * current quantity / bom finished product quantity
            if component_line['prod_id'] == butter.id:
                # 5 kg of butter at 7.01$ for 11kg of crumble -> / 11 for price per unit (3.19)
                self.assertEqual(float_compare(component_line['total'], (7.01 * 5) * (1 / 11), precision_digits=2), 0)
            if component_line['prod_id'] == biscuit.id:
                # 6 kg of biscuits at 1.50$ for 11kg of crumble -> / 11 for price per unit (0.82)
                self.assertEqual(float_compare(component_line['total'], (1.5 * 6) * (1 / 11), precision_digits=2), 0)
        # total price = 3.19 + 0.82 + operation_cost(0.83 + 0.83 + 0.5 = 2.16) = 6,17
        self.assertEqual(float_compare(report_values['lines']['total'], 6.17, precision_digits=2), 0, 'Product Unit Bom Price is not correct')

        # TEST OPERATION COST WHEN PRODUCED QTY > BOM QUANTITY
        report_values_12 = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=12, searchVariant=False)
        report_values_22 = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=22, searchVariant=False)
        operation_cost = float_round(10 / 60 * 10, precision_digits=2) * 2 + float_round(6 / 60 * 10, precision_digits=2)
        # Both needs 2 operation cycle
        self.assertEqual(report_values_12['lines']['operations_cost'], report_values_22['lines']['operations_cost'])
        self.assertEqual(report_values_22['lines']['operations_cost'], operation_cost)
        report_values_23 = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=23, searchVariant=False)
        operation_cost = float_round(15 / 60 * 10, precision_digits=2) * 2 + float_round(9 / 60 * 10, precision_digits=2)
        self.assertEqual(report_values_23['lines']['operations_cost'], operation_cost)

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

        with Form(bom_cheese_cake) as bom:
            with bom.bom_line_ids.new() as line:
                line.product_id = cream
                line.product_uom_id = uom_litre
                line.product_qty = 3
            with bom.bom_line_ids.new() as line:
                line.product_id = crumble
                line.product_uom_id = uom_kg
                line.product_qty = 5.4

        workcenter_2 = self.env['mrp.workcenter'].create({
            'name': 'cake mounting',
            'costs_hour': 20,
            'time_start': 10,
            'time_stop': 15
        })

        routing_form = Form(self.env['mrp.routing'])
        routing_form.name = "Cheese cake process"
        routing_cheese = routing_form.save()

        with Form(routing_cheese) as routing:
            with routing.operation_ids.new() as operation:
                operation.workcenter_id = workcenter
                operation.name = 'Mix cheese and crumble'
                operation.time_cycle_manual = 10
            with routing.operation_ids.new() as operation:
                operation.workcenter_id = workcenter_2
                operation.name = 'Cake mounting'
                operation.time_cycle_manual = 5

        bom_cheese_cake.routing_id = routing_cheese.id

        # TEST CHEESE BOM STRUCTURE VALUE WITH BOM QUANTITY
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_cheese_cake.id, searchQty=60, searchVariant=False)
        self.assertEqual(report_values['lines']['operations_time'], 40.0, 'Operation time should be the same for 1 unit or for the batch')
        # Operation cost is the sum of operation line.
        operation_cost = float_round(10 / 60 * 10, precision_digits=2) + float_round(30 / 60 * 20, precision_digits=2)
        self.assertEqual(float_compare(report_values['lines']['operations_cost'], operation_cost, precision_digits=2), 0)

        for component_line in report_values['lines']['components']:
            # standard price * bom line quantity * current quantity / bom finished product quantity
            if component_line['prod_id'] == cream.id:
                # 3 liter of cream at 5.17$ for 60 unit of cheese cake -> 15.51$
                self.assertEqual(float_compare(component_line['total'], (3 * 5.17), precision_digits=2), 0)
            if component_line['prod_id'] == crumble.id:
                # 5.4 kg of crumble at the cost of a batch.
                crumble_cost = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_crumble.id, searchQty=5.4, searchVariant=False)['lines']['total']
                self.assertEqual(float_compare(component_line['total'], crumble_cost, precision_digits=2), 0)
        # total price = 15.51 + crumble_cost + operation_cost(10 + 1.67 = 11.67) = 27.18 + crumble_cost
        self.assertEqual(float_compare(report_values['lines']['total'], 27.18 + crumble_cost, precision_digits=2), 0, 'Product Bom Price is not correct')

    def test_bom_report_variant(self):
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

        self.car_gps_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.car.id,
            'attribute_id': self.gps_attribute.id,
            'value_ids': [(6, 0, [self.gps_yes.id, self.gps_no.id])],
        })

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

        self.car_color_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.car.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id, self.color_blue.id])],
        })

        self.car.create_variant_ids()

        # Blue and red paint
        uom_litre = self.env.ref('uom.product_uom_litre')
        self.paint = self.env['product.template'].create({
            'name': 'Paint',
            'uom_id': uom_litre.id,
            'uom_po_id': uom_litre.id
        })
        self.paint_color_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.paint.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id, self.color_blue.id])],
        })

        self.paint.create_variant_ids()
        self.paint.product_variant_ids.write({'standard_price': 20})

        self.dashboard = self.env['product.template'].create({
            'name': 'Dashboard',
            'standard_price': 1000,
        })

        self.dashboard_gps_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.dashboard.id,
            'attribute_id': self.gps_attribute.id,
            'value_ids': [(6, 0, [self.gps_yes.id, self.gps_no.id])],
        })
        self.dashboard_color_attribute_lines = self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.dashboard.id,
            'attribute_id': self.color_attribute.id,
            'value_ids': [(6, 0, [self.color_red.id, self.color_blue.id])],
        })

        self.dashboard.create_variant_ids()

        self.gps = self.env['product.product'].create({
            'name': 'GPS',
            'standard_price': 700,
        })

        bom_form_car = Form(self.env['mrp.bom'])
        bom_form_car.product_tmpl_id = self.car
        bom_form_car.product_qty = 5
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.paint.id), ('attribute_value_ids', '=', self.color_red.id)])
            line.product_uom_id = uom_litre
            line.product_qty = 50
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.paint.id), ('attribute_value_ids', '=', self.color_blue.id)])
            line.product_uom_id = uom_litre
            line.product_qty = 50
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.dashboard.id), ('attribute_value_ids', '=', self.gps_yes.id), ('attribute_value_ids', '=', self.color_red.id)])
            line.product_qty = 5
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.dashboard.id), ('attribute_value_ids', '=', self.gps_yes.id), ('attribute_value_ids', '=', self.color_blue.id)])
            line.product_qty = 5
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.dashboard.id), ('attribute_value_ids', '=', self.gps_no.id), ('attribute_value_ids', '=', self.color_red.id)])
            line.product_qty = 5
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.dashboard.id), ('attribute_value_ids', '=', self.gps_no.id), ('attribute_value_ids', '=', self.color_blue.id)])
            line.product_qty = 5
        bom_car = bom_form_car.save()

        for attribute in self.gps_attribute.value_ids | self.color_attribute.value_ids:
            bom_car.bom_line_ids.filtered(lambda l: attribute in l.product_id.attribute_value_ids).write({'attribute_value_ids': [(4, attribute.id)]})

        bom_dashboard = Form(self.env['mrp.bom'])
        bom_dashboard.product_tmpl_id = self.dashboard
        bom_dashboard.product_qty = 2
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.paint.id), ('attribute_value_ids', '=', self.color_red.id)])
            line.product_uom_id = uom_litre
            line.product_qty = 1
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.env['product.product'].search([('product_tmpl_id', '=', self.paint.id), ('attribute_value_ids', '=', self.color_blue.id)])
            line.product_uom_id = uom_litre
            line.product_qty = 1
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.gps
            line.product_qty = 2
        bom_dashboard = bom_dashboard.save()

        for attribute in self.color_attribute.value_ids:
            bom_dashboard.bom_line_ids.filtered(lambda l: attribute in l.product_id.attribute_value_ids).write({'attribute_value_ids': [(4, attribute.id)]})
        bom_dashboard.bom_line_ids.filtered(lambda l: l.product_id == self.gps).write({'attribute_value_ids': [(4, self.gps_yes.id)]})

        blue_car_with_gps = self.env['product.product'].search([
            ('product_tmpl_id', '=', self.car.id),
            ('attribute_value_ids', '=', self.gps_yes.id),
            ('attribute_value_ids', '=', self.color_blue.id)
        ])
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_car.id, searchQty=1, searchVariant=blue_car_with_gps.id)
        # Two lines. blue dashboard with gps and blue paint.
        self.assertEqual(len(report_values['lines']['components']), 2)

        # 10l of blue paint
        blue_paint = self.env['product.product'].search([
            ('product_tmpl_id', '=', self.paint.id),
            ('attribute_value_ids', '=', self.color_blue.id)
        ])
        self.assertEqual(blue_paint.id, report_values['lines']['components'][0]['prod_id'])
        self.assertEqual(report_values['lines']['components'][0]['prod_qty'], 10)
        # 1 blue dashboard with GPS
        blue_dashboard_gps = self.env['product.product'].search([
            ('product_tmpl_id', '=', self.dashboard.id),
            ('attribute_value_ids', '=', self.gps_yes.id),
            ('attribute_value_ids', '=', self.color_blue.id)
        ])
        self.assertEqual(blue_dashboard_gps.id, report_values['lines']['components'][1]['prod_id'])
        self.assertEqual(report_values['lines']['components'][1]['prod_qty'], 1)
        component = report_values['lines']['components'][1]
        report_values_dashboad = self.env['report.mrp.report_bom_structure']._get_bom(
            component['child_bom'], component['prod_id'], component['prod_qty'],
            component['line_id'], component['level'] + 1)

        self.assertEqual(len(report_values_dashboad['components']), 2)
        self.assertEqual(blue_paint.id, report_values_dashboad['components'][0]['prod_id'])
        self.assertEqual(self.gps.id, report_values_dashboad['components'][1]['prod_id'])

        # 0.5l of paint at price of 20$/litre -> 10$
        self.assertEqual(report_values_dashboad['components'][0]['total'], 10)
        # GPS 700$
        self.assertEqual(report_values_dashboad['components'][1]['total'], 700)

        # Dashboard blue with GPS should have a BoM cost of 710$
        self.assertEqual(report_values['lines']['components'][1]['total'], 710)
        # 10l of paint at price of 20$/litre -> 200$
        self.assertEqual(report_values['lines']['components'][0]['total'], 200)

        # Total cost of blue car with GPS: 10 + 700 + 200 = 910
        self.assertEqual(report_values['lines']['total'], 910)

        red_car_without_gps = self.env['product.product'].search([
            ('product_tmpl_id', '=', self.car.id),
            ('attribute_value_ids', '=', self.gps_no.id),
            ('attribute_value_ids', '=', self.color_red.id)
        ])
        report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=bom_car.id, searchQty=1, searchVariant=red_car_without_gps.id)
        # Same math than before but without GPS
        self.assertEqual(report_values['lines']['total'], 210)
