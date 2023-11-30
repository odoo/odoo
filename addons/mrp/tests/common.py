# -*- coding: utf-8 -*-

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.stock.tests.common import TestStockCommon
from odoo.addons.product.tests.common import TestProductCommon


class TestMrpCommon(TestStockCommon, TestProductCommon):

    @classmethod
    def generate_mo(cls, tracking_final='none', tracking_base_1='none', tracking_base_2='none', qty_final=5, qty_base_1=4, qty_base_2=1, picking_type_id=False, consumption=False):
        """ This function generate a manufacturing order with one final
        product and two consumed product. Arguments allows to choose
        the tracking/qty for each different products. It returns the
        MO, used bom and the tree products.
        """
        product_to_build = cls.env['product.product'].create({
            'name': 'Young Tom',
            'type': 'product',
            'tracking': tracking_final,
        })
        product_to_use_1 = cls.env['product.product'].create({
            'name': 'Botox',
            'type': 'product',
            'tracking': tracking_base_1,
        })
        product_to_use_2 = cls.env['product.product'].create({
            'name': 'Old Tom',
            'type': 'product',
            'tracking': tracking_base_2,
        })
        bom_1 = cls.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'consumption': consumption if consumption else 'flexible',
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use_1.id, 'product_qty': qty_base_1}),
                (0, 0, {'product_id': product_to_use_2.id, 'product_qty': qty_base_2}),
            ]})
        mo = cls.env['mrp.production'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': qty_final,
            'bom_id': bom_1.id,
        })
        mo.action_confirm()
        return mo, bom_1, product_to_build, product_to_use_1, product_to_use_2

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        (
            cls.product_4,
            cls.product_3,
            cls.product_5,
            cls.product_6,
            cls.product_8,
        ) = cls.env['product.product'].create([{
            'name': 'Stick',  # product_4
            'uom_id': cls.uom_dozen.id,
            'uom_po_id': cls.uom_dozen.id,
        }, {
            'name': 'Bench',  # product_3
        }, {
            'name': 'Stone Tools',  # product_5
        }, {
            'name': 'Door',  # product_6
        }, {
            'name': 'House',  # product_8
        }])

        # Update demo products
        (cls.product_1 | cls.product_2 | cls.product_3 | cls.product_4 | cls.product_5 | cls.product_6 | cls.product_7_3 | cls.product_8).write({
            'type': 'product',
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
        cls.env.user.groups_id += cls.env.ref('uom.group_uom') + cls.env.ref('mrp.group_mrp_routings')

        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.workcenter_2 = cls.env['mrp.workcenter'].create({
            'name': 'Simple Workcenter',
            'default_capacity': 1,
            'time_start': 0,
            'time_stop': 0,
            'time_efficiency': 100,
        })
        cls.workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Double Workcenter',
            'default_capacity': 2,
            'time_start': 0,
            'time_stop': 0,
            'time_efficiency': 100,
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
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 4})
            ]})
        cls.bom_kit_op = cls.env['mrp.bom'].create({
            'product_id': cls.product_5.id,
            'product_tmpl_id': cls.product_5.product_tmpl_id.id,
            'product_uom_id': cls.product_5.uom_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Gift Wrap Maching', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 15, 'sequence': 1}),
            ],
            'type': 'phantom',
            'sequence': 2,
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_4.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_3.id, 'product_qty': 3})
            ]})
        cls.bom_3 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'product_uom_id': cls.uom_dozen.id,
            'ready_to_produce': 'asap',
            'consumption': 'flexible',
            'product_qty': 2.0,
            'operation_ids': [
                (0, 0, {'name': 'Cutting Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 12, 'sequence': 1}),
                (0, 0, {'name': 'Weld Machine', 'workcenter_id': cls.workcenter_1.id, 'time_cycle': 18, 'sequence': 2}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_5.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_4.id, 'product_qty': 8}),
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 12})
            ]})
        cls.bom_4 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Rub it gently with a cloth', 'workcenter_id': cls.workcenter_2.id,
                        'time_mode_batch': 1, 'time_mode': "auto", 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 1}),
            ]})
        cls.stock_location_14 = cls.env['stock.location'].create({
            'name': 'Shelf 2',
            'location_id': cls.env.ref('stock.warehouse0').lot_stock_id.id,
        })
        cls.stock_location_components = cls.env['stock.location'].create({
            'name': 'Shelf 1',
            'location_id': cls.env.ref('stock.warehouse0').lot_stock_id.id,
        })
        cls.laptop = cls.env['product.product'].create({
            'name': 'Acoustic Bloc Screens',
            'uom_id': cls.env.ref("uom.product_uom_unit").id,
            'uom_po_id': cls.env.ref("uom.product_uom_unit").id,
            'type': 'product',
            'tracking': 'none',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.graphics_card = cls.env['product.product'].create({
            'name': 'Individual Workplace',
            'uom_id': cls.env.ref("uom.product_uom_unit").id,
            'uom_po_id': cls.env.ref("uom.product_uom_unit").id,
            'type': 'product',
            'tracking': 'none',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.mo, cls.bom, cls.product_to_build, cls.product_to_use_1, cls.product_to_use_2 = cls.generate_mo()
        cls.stock_location = cls.env.ref('stock.stock_location_stock')
        cls.env['stock.quant']._update_available_quantity(cls.product_to_use_1, cls.stock_location, 100)
        cls.env['stock.quant']._update_available_quantity(cls.product_to_use_2, cls.stock_location, 5)

    @classmethod
    def make_prods(cls, n):
        return [
            cls.env["product.product"].create(
                {"name": f"p{k + 1}", "type": "product"}
            )
            for k in range(n)
        ]

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
                    (0, 0, {
                        "product_id": c.id,
                        "product_qty": 1,
                        "product_uom_id": cls.uom_unit.id
                    })
                    for c in cs
                ],
            }
        )
