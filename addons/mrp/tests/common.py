# -*- coding: utf-8 -*-

from odoo.addons.stock.tests import common2


class TestMrpCommon(common2.TestStockCommon):

    @classmethod
    def generate_mo(self, tracking_final='none', tracking_base_1='none', tracking_base_2='none', qty_final=5, qty_base_1=4, qty_base_2=1):
        """ This function generate a manufacturing order with one final
        product and two consumed product. Arguments allows to choose
        the tracking/qty for each different products. It returns the
        MO, used bom and the tree products.
        """
        product_to_build = self.env['product.product'].create({
            'name': 'Young Tom',
            'type': 'product',
            'tracking': tracking_final,
        })
        product_to_use_1 = self.env['product.product'].create({
            'name': 'Botox',
            'type': 'product',
            'tracking': tracking_base_1,
        })
        product_to_use_2 = self.env['product.product'].create({
            'name': 'Old Tom',
            'type': 'product',
            'tracking': tracking_base_2,
        })
        bom_1 = self.env['mrp.bom'].create({
            'product_id': product_to_build.id,
            'product_tmpl_id': product_to_build.product_tmpl_id.id,
            'product_uom_id': self.uom_unit.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': product_to_use_2.id, 'product_qty': qty_base_2}),
                (0, 0, {'product_id': product_to_use_1.id, 'product_qty': qty_base_1})
            ]})
        mo = self.env['mrp.production'].create({
            'name': 'MO 1',
            'product_id': product_to_build.id,
            'product_uom_id': product_to_build.uom_id.id,
            'product_qty': qty_final,
            'bom_id': bom_1.id,
        })
        return mo, bom_1, product_to_build, product_to_use_1, product_to_use_2

    @classmethod
    def setUpClass(cls):
        super(TestMrpCommon, cls).setUpClass()

        # Fetch mrp-related user groups
        user_group_mrp_user = cls.env.ref('mrp.group_mrp_user')
        user_group_mrp_manager = cls.env.ref('mrp.group_mrp_manager')

        # Update demo products
        (cls.product_2 | cls.product_3 | cls.product_4 | cls.product_5 | cls.product_6 | cls.product_7 | cls.product_8).write({
            'type': 'product',
        })

        # User Data: mrp user and mrp manager
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_mrp_user = Users.create({
            'name': 'Hilda Ferachwal',
            'login': 'hilda',
            'email': 'h.h@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_mrp_user.id])]})
        cls.user_mrp_manager = Users.create({
            'name': 'Gary Youngwomen',
            'login': 'gary',
            'email': 'g.g@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_mrp_manager.id])]})

        cls.workcenter_1 = cls.env['mrp.workcenter'].create({
            'name': 'Nuclear Workcenter',
            'capacity': 2,
            'time_start': 10,
            'time_stop': 5,
            'time_efficiency': 80,
        })
        cls.routing_1 = cls.env['mrp.routing'].create({
            'name': 'Simple Line',
        })
        cls.routing_2 = cls.env['mrp.routing'].create({
            'name': 'Complicated Line',
        })
        cls.operation_1 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Gift Wrap Maching',
            'workcenter_id': cls.workcenter_1.id,
            'routing_id': cls.routing_1.id,
            'time_cycle': 15,
            'sequence': 1,
        })
        cls.operation_2 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Cutting Machine',
            'workcenter_id': cls.workcenter_1.id,
            'routing_id': cls.routing_2.id,
            'time_cycle': 12,
            'sequence': 1,
        })
        cls.operation_3 = cls.env['mrp.routing.workcenter'].create({
            'name': 'Weld Machine',
            'workcenter_id': cls.workcenter_1.id,
            'routing_id': cls.routing_2.id,
            'time_cycle': 18,
            'sequence': 2,
        })

        cls.bom_1 = cls.env['mrp.bom'].create({
            'product_id': cls.product_4.id,
            'product_tmpl_id': cls.product_4.product_tmpl_id.id,
            'product_uom_id': cls.uom_unit.id,
            'product_qty': 4.0,
            'routing_id': cls.routing_2.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_1.id, 'product_qty': 4})
            ]})
        cls.bom_2 = cls.env['mrp.bom'].create({
            'product_id': cls.product_5.id,
            'product_tmpl_id': cls.product_5.product_tmpl_id.id,
            'product_uom_id': cls.product_5.uom_id.id,
            'product_qty': 1.0,
            'routing_id': cls.routing_1.id,
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
            'product_qty': 2.0,
            'routing_id': cls.routing_2.id,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_5.id, 'product_qty': 2}),
                (0, 0, {'product_id': cls.product_4.id, 'product_qty': 8}),
                (0, 0, {'product_id': cls.product_2.id, 'product_qty': 12})
            ]})
