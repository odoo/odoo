# -*- coding: utf-8 -*-

from odoo.addons.product.tests import common


class TestStockCommon(common.TestProductCommon):

    def _create_procurement(self, user, **values):
        Procurement = self.env['procurement.order'].sudo(user)
        procurement = Procurement.new(values)
        procurement.onchange_product_id()
        return Procurement.create(procurement._convert_to_write(procurement._cache))

    @classmethod
    def setUpClass(cls):
        super(TestStockCommon, cls).setUpClass()

        user_group_employee = cls.env.ref('base.group_user')

        # User Data: lambda user
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_employee = Users.create({
            'name': 'Fabricette Manivelle',
            'login': 'fabricette',
            'email': 'f.f@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [user_group_employee.id])]})
