# -*- coding: utf-8 -*-

from openerp.addons.mail.tests.common import TestMail


class TestCrm(TestMail):

    @classmethod
    def setUpClass(cls):
        super(TestCrm, cls).setUpClass()

        user_group_employee = cls.env.ref('base.group_user')
        user_group_salesman_all = cls.env.ref('base.group_sale_salesman_all_leads')

        # Test users to use through the various tests
        Users = cls.env['res.users'].with_context({'no_reset_password': True, 'mail_create_nosubscribe': True})
        cls.user_salesman_all = Users.create({
            'name': 'Riton La Chignole',
            'login': 'riton',
            'alias_name': 'riton',
            'email': 'riton.salesman_all@example.com',
            'groups_id': [(6, 0, [user_group_employee.id, user_group_salesman_all.id])]})

        cls.sales_team_1 = cls.env['crm.team'].create({
            'name': 'Test Sales Team',
            'alias_name': 'test_sales_team',
        })
