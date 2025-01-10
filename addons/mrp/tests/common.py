# -*- coding: utf-8 -*-

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
        product_to_build = cls.ProductObj.create({
            'name': 'Young Tom',
            'type': 'consu',
            'is_storable': True,
            'tracking': tracking_final,
        })
        product_to_use_1 = cls.ProductObj.create({
            'name': 'Botox',
            'type': 'consu',
            'is_storable': True,
            'tracking': tracking_base_1,
        })
        product_to_use_2 = cls.ProductObj.create({
            'name': 'Old Tom',
            'type': 'consu',
            'is_storable': True,
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
                (0, 0, {'product_id': product_to_use_2.id, 'product_qty': qty_base_2, 'manual_consumption': tracking_base_2 != 'none'}),
                (0, 0, {'product_id': product_to_use_1.id, 'product_qty': qty_base_1, 'manual_consumption': tracking_base_1 != 'none'})
            ],
            'company_id': cls.stock_company.id,
        })
        mo_form = Form(cls.env['mrp.production'])
        mo_form.product_id = product_to_build
        mo_form.company_id = cls.stock_company
        if picking_type_id:
            mo_form.picking_type_id = picking_type_id
        mo_form.bom_id = bom_1
        mo_form.product_qty = qty_final
        mo = mo_form.save()
        mo.action_confirm()
        return mo, bom_1, product_to_build, product_to_use_1, product_to_use_2

    def setUp(self):
        super().setUp()
        self.uid = self.user_stock_manager

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # User Data: mrp user and mrp manager
        cls.user_mrp_user = mail_new_test_user(
            cls.env,
            name='Hilda Ferachwal',
            login='hilda',
            email='h.h@example.com',
            notification_type='inbox',
            groups='mrp.group_mrp_user, mrp.group_mrp_byproducts, uom.group_uom',
            company_id=cls.env.company.id,
        )
        cls.user_mrp_manager = mail_new_test_user(
            cls.env,
            name='Gary Youngwomen',
            login='gary',
            email='g.g@example.com',
            notification_type='inbox',
            groups='mrp.group_mrp_manager, mrp.group_mrp_byproducts, uom.group_uom',
            company_id=cls.env.company.id,
        )

        (
            cls.product_4,
            cls.product_5,
            cls.product_6,
            cls.product_8,
        ) = cls.ProductObj.create([{
            'name': 'Stick',  # product_4
            'uom_id': cls.uom_dozen.id,
            'uom_po_id': cls.uom_dozen.id,
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

        # Groups below are required to make fields `product_uom_id` and
        # `workorder_ids` to be visible in the view of `mrp.production`. The
        # field `product_uom_id` must be set by many tests, and subviews of
        # `workorder_ids` must be present in many tests to create records.
        cls.user_stock_user.groups_id += \
            cls.env.ref('uom.group_uom') + \
            cls.env.ref('mrp.group_mrp_user') + \
            cls.env.ref('mrp.group_mrp_routings')

        cls.user_stock_manager.groups_id += \
            cls.env.ref('uom.group_uom') + \
            cls.env.ref('mrp.group_mrp_manager') + \
            cls.env.ref('mrp.group_mrp_routings')

        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'default_capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
            'company_id': cls.stock_company.id,
            'resource_calendar_id': cls.stock_company.resource_calendar_id.id,
        })
        cls.workcenter_2 = cls.env['mrp.workcenter'].create({
            'name': 'Simple Workcenter',
            'default_capacity': 1,
            'time_start': 0,
            'time_stop': 0,
            'time_efficiency': 100,
            'company_id': cls.stock_company.id,
            'resource_calendar_id': cls.stock_company.resource_calendar_id.id,
        })
        cls.workcenter_3 = cls.env['mrp.workcenter'].create({
            'name': 'Double Workcenter',
            'default_capacity': 2,
            'time_start': 0,
            'time_stop': 0,
            'time_efficiency': 100,
            'company_id': cls.stock_company.id,
            'resource_calendar_id': cls.stock_company.resource_calendar_id.id,
        })
        cls.calendar = cls.stock_company.resource_calendar_id

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
            ],
            'company_id': cls.stock_company.id,
        })
        cls.bom_2 = cls.env['mrp.bom'].create({
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
            ],
            'company_id': cls.stock_company.id,
        })
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
            ],
            'company_id': cls.stock_company.id,
        })
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
            ],
            'company_id': cls.stock_company.id,
        })
        cls.bom_5 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Rub it gently with a cloth two at once', 'workcenter_id': cls.workcenter_3.id,
                        'time_mode_batch': 2, 'time_mode': "auto", 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 1}),
            ],
            'company_id': cls.stock_company.id,
        })
        cls.bom_6 = cls.env['mrp.bom'].create({
            'product_id': cls.product_6.id,
            'product_tmpl_id': cls.product_6.product_tmpl_id.id,
            'consumption': 'flexible',
            'product_qty': 1.0,
            'operation_ids': [
                (0, 0, {'name': 'Rub it gently with a cloth two at once', 'workcenter_id': cls.workcenter_3.id,
                        'time_mode_batch': 1, 'time_mode': "auto", 'sequence': 1}),
            ],
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 1}),
            ],
            'company_id': cls.stock_company.id,
        })

        cls.pbm_location = cls.warehouse_1.pbm_loc_id
        cls.stock_location_14 = cls.StockLocationObj.create({
            'name': 'Shelf 2',
            'location_id': cls.stock_location.id,
            'company_id': cls.stock_company.id,
        })
        cls.stock_location_components = cls.StockLocationObj.create({
            'name': 'Shelf 1',
            'location_id': cls.stock_location.id,
            'company_id': cls.stock_company.id,
        })
        cls.laptop = cls.ProductObj.create({
            'name': 'Acoustic Bloc Screens',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'type': 'consu',
            'is_storable': True,
            'tracking': 'none',
        })
        cls.graphics_card = cls.ProductObj.create({
            'name': 'Individual Workplace',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'type': 'consu',
            'is_storable': True,
            'tracking': 'none',
        })

    @classmethod
    def make_prods(cls, n):
        return [
            cls.ProductObj.create(
                {"name": f"p{k + 1}", 'is_storable': True}
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

    @classmethod
    def _enable_mrp_byproducts(cls, user=None):
        user = user or cls.user
        user.groups_id += cls.env.ref('mrp.group_mrp_byproducts')
