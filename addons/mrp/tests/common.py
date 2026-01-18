
from odoo import Command
from odoo.tests import Form

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.stock.tests.common import TestStockCommon


class TestMrpCommon(TestStockCommon):

    @classmethod
    def generate_mo(cls, tracking_final='none', tracking_base_1='none', tracking_base_2='none', qty_final=5, qty_base_1=4, qty_base_2=1, picking_type_id=False, consumption=False):
        """ This function generate a manufacturing order with one final
        product and two consumed product. Arguments allows to choose
        the tracking/qty for each different products. It returns the
        MO, used bom and the tree products.
        """
        product_to_build, product_to_use_1, product_to_use_2 = cls.env['product.product'].create([
            {
                'name': 'Young Tom',
                'type': 'consu',
                'is_storable': True,
                'tracking': tracking_final,
            }, {
                'name': 'Botox',
                'type': 'consu',
                'is_storable': True,
                'tracking': tracking_base_1,
            }, {
                'name': 'Old Tom',
                'type': 'consu',
                'is_storable': True,
                'tracking': tracking_base_2,
            }
        ])
        bom_1 = cls.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': consumption if consumption else 'flexible',
            'bom_line_ids': [
                Command.create({'product_id': product_to_use_2.id, 'product_qty': qty_base_2}),
                Command.create({'product_id': product_to_use_1.id, 'product_qty': qty_base_1}),
            ],
        })
        mo_form = Form(cls.env['mrp.production'])
        mo_form.product_id = product_to_build
        if picking_type_id:
            mo_form.picking_type_id = picking_type_id
        mo_form.bom_id = bom_1
        mo_form.product_qty = qty_final
        mo = mo_form.save()
        mo.action_confirm()
        return mo, bom_1, product_to_build, product_to_use_1, product_to_use_2

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_mrp_routings = cls.quick_ref('mrp.group_mrp_routings')

        # Kept for reduced diff in existing tests, should be dropped someday
        cls.product_7_template = cls.product_template_sofa

        cls.product_7_attr1_v1 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[0]
        cls.product_7_attr1_v2 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[1]
        cls.product_7_attr1_v3 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[2]

        cls.product_7_1 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v1)
        cls.product_7_2 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v2)
        cls.product_7_3 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v3)

        (
            cls.product_4,
            cls.product_5,
            cls.product_6,
            cls.product_8,
        ) = cls.env['product.product'].create([{
            'name': 'Stick',  # product_4
            'uom_id': cls.uom_dozen.id,
        }, {
            'name': 'Stone Tools',  # product_5
        }, {
            'name': 'Door',  # product_6
        }, {
            'name': 'House',  # product_8
        }])

        # Update demo products
        (cls.product_2 | cls.product_3 | cls.product_4 | cls.product_5 | cls.product_6 | cls.product_7_3 | cls.product_8).write({
            'type': 'consu',
            'is_storable': True,
        })

        # User Data: mrp user and mrp manager
        cls.user_mrp_user = mail_new_test_user(
            cls.env,
            name='Hilda Ferachwal',
            login='hilda',
            email='h.h@example.com',
            notification_type='inbox',
            groups='mrp.group_mrp_user, stock.group_stock_user, mrp.group_mrp_byproducts, uom.group_uom',
        )
        cls.user_mrp_manager = mail_new_test_user(
            cls.env,
            name='Gary Youngwomen',
            login='gary',
            email='g.g@example.com',
            notification_type='inbox',
            groups='mrp.group_mrp_manager, stock.group_stock_user, mrp.group_mrp_byproducts, uom.group_uom',
        )
        # Both groups below are required to make fields `product_uom_id` and
        # `workorder_ids` to be visible in the view of `mrp.production`. The
        # field `product_uom_id` must be set by many tests, and subviews of
        # `workorder_ids` must be present in many tests to create records.
        cls.env.user.group_ids += cls.group_uom + cls.group_mrp_routings
        cls.picking_type_manu = cls.warehouse_1.manu_type_id
        cls.picking_type_manu.sequence = 5
        cls.route_manufacture = cls.warehouse_1.manufacture_pull_id.route_id

        cls.workcenter_1, cls.workcenter_2, cls.workcenter_3 = cls.env['mrp.workcenter'].create([
            {
                'name': 'Nuclear Workcenter',
                'time_start': 10,
                'time_stop': 5,
                'time_efficiency': 80,
            }, {
                'name': 'Simple Workcenter',
                'time_start': 0,
                'time_stop': 0,
                'time_efficiency': 100,
            }, {
                'name': 'Double Workcenter',
                'time_start': 0,
                'time_stop': 0,
                'time_efficiency': 100,
            }
        ])
        for (workcenter, default_capacity) in [(cls.workcenter_1, 2), (cls.workcenter_2, 1), (cls.workcenter_3, 2)]:
            cls.env['mrp.workcenter.capacity'].create({
                'workcenter_id': workcenter.id,
                'product_uom_id': cls.uom_unit.id,
                'capacity': default_capacity,
                'time_start': workcenter.time_start,
                'time_stop': workcenter.time_stop,
            })
        cls.bom_1 = cls.env['mrp.bom'].create({
            'product_id': cls.product_4.id,
            'product_tmpl_id': cls.product_4.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 4.0,
            'consumption': 'flexible',
            'operation_ids': [
            ],
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.product_2.id, 'product_qty': 2}),
                Command.create({'product_id': cls.product_1.id, 'product_qty': 4}),
            ]})
        cls.bom_2 = cls.env['mrp.bom'].create({
            'product_id': cls.product_5.id,
            'product_tmpl_id': cls.product_5.product_tmpl_id.id,
            'product_uom_id': cls.product_5.uom_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [
                Command.create({'name': 'Gift Wrap Maching', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
            'type': 'phantom',
            'sequence': 2,
            'bom_line_ids': [
                Command.create({'product_id': cls.product_4.id, 'product_qty': 2}),
                Command.create({'product_id': cls.product_3.id, 'product_qty': 3}),
            ]})
        cls.bom_3 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'product_uom_id': cls.uom_dozen.id,
            'ready_to_produce': 'asap',
            'consumption': 'flexible',
            'product_qty': 2.0,
            'operation_ids': [
                Command.create({'name': 'Cutting Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                Command.create({'name': 'Weld Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 18, 'sequence': 2}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.product_5.id, 'product_qty': 2}),
                Command.create({'product_id': cls.product_4.id, 'product_qty': 8}),
                Command.create({'product_id': cls.product_2.id, 'product_qty': 12}),
            ]})
        cls.bom_4 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [Command.create({
                'name': 'Rub it gently with a cloth',
                'workcenter_id': cls.workcenter_2.id,
                'time_mode_batch': 1,
                'time_mode': "auto",
                'sequence': 1,
            })],
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.product_1.id, 'product_qty': 1}),
            ]})
        cls.bom_5 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [Command.create({
                'name': 'Rub it gently with a cloth two at once',
                'workcenter_id': cls.workcenter_3.id,
                'time_mode_batch': 2,
                'time_mode': "auto",
                'sequence': 1,
            })],
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.product_1.id, 'product_qty': 1}),
            ]})
        cls.bom_6 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [Command.create({
                'name': 'Rub it gently with a cloth two at once',
                'workcenter_id': cls.workcenter_3.id,
                'time_mode_batch': 1,
                'time_mode': "auto",
                'sequence': 1,
            })],
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.product_1.id, 'product_qty': 1}),
            ]})

        cls.stock_location_components = cls.shelf_1

    @classmethod
    def make_bom(cls, p, *cs):
        return cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": p.product_tmpl_id.id,
                "product_id": p.id,
                "product_qty": 1,
                "type": "phantom",
                "product_uom_id": cls.uom_unit.id,
                "bom_line_ids": [
                    Command.create({
                        "product_id": c.id,
                        "product_qty": 1,
                        "product_uom_id": cls.uom_unit.id
                    })
                    for c in cs
                ],
            }
        )

    def full_availability(self):
        """set full availability for all calendars"""
        calendar = self.env['resource.calendar'].search([])
        calendar.write({'attendance_ids': [(5, 0, 0)]})
        calendar.write({'attendance_ids': [
            (0, 0, {'name': 'Monday', 'dayofweek': '0', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Tuesday', 'dayofweek': '1', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Wednesday', 'dayofweek': '2', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Thursday', 'dayofweek': '3', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Friday', 'dayofweek': '4', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Saturday', 'dayofweek': '5', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
            (0, 0, {'name': 'Sunday', 'dayofweek': '6', 'hour_from': 0, 'hour_to': 24, 'day_period': 'morning'}),
        ]})
