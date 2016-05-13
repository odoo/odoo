# -*- coding: utf-8 -*-

from odoo.addons.stock.tests import common2


class TestMrpCommon(common2.TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMrpCommon, cls).setUpClass()

        # Fetch mrp-related user groups
        user_group_mrp_user = cls.env.ref('mrp.group_mrp_user')
        user_group_mrp_manager = cls.env.ref('mrp.group_mrp_manager')

        # User Data: stock user and stock manager
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_mrp_user = Users.create({
            'name': 'Hilda Ferachwal',
            'login': 'hilda',
            'email': 'h.h@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [user_group_mrp_user.id])]})
        cls.user_mrp_manager = Users.create({
            'name': 'Gary Youngwomen',
            'login': 'gary',
            'email': 'g.g@example.com',
            'notify_email': 'none',
            'groups_id': [(6, 0, [user_group_mrp_manager.id])]})

        cls.bom_1 = cls.env['mrp.bom'].create({
            'product_id': cls.product_1.id,
            'product_tmpl_id': cls.product_1.product_tmpl_id.id,
            'product_uom_id': cls.product_1.uom_id.id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.product_2.id}),
                (0, 0, {'product_id': cls.product_3.id})
            ]})

        cls.production_1 = cls.env['mrp.production'].create({
            'name': 'MO-Test',
            'product_id': cls.product_1.id,
            'product_qty': 1.0,
            'bom_id': cls.bom_1.id,
            'product_uom_id': cls.product_1.uom_id.id,
        })
