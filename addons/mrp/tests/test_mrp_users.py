# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestMrpUsers(common.TransactionCase):

    def setUp(self):
        super(TestMrpUsers, self).setUp()

        self.ResUsers = self.env['res.users']
        self.res_users_mrp_manager = self.env.ref('mrp.group_mrp_manager')
        self.group_account_user = self.env.ref('account.group_account_user')
        self.main_company = self.env.ref('base.main_company')
        self.group_mrp_user = self.env.ref('mrp.group_mrp_user')

        # Create a user as 'MRP Manager'
        # I added groups for MRP Manager.

        self.res_users_mrp_manager = self.ResUsers.create({
            'company_id': self.main_company.id,
            'name': 'MRP Manager',
            'login': 'mam',
            'password': 'mam',
            'email': 'mrp_manager@yourcompany.com',
            'groups_id': [(6, 0, [self.res_users_mrp_manager.id, self.group_account_user.id])]
        })

        # Create a user as 'MRP User'
        # I added groups for MRP User.
        self.res_users_mrp_user = self.ResUsers.create({
            'company_id': self.main_company.id,
            'name': 'MRP User',
            'login': 'mau',
            'password': 'mau',
            'email': 'mrp_user@yourcompany.com',
            'groups_id': [(6, 0, [self.group_mrp_user.id])]
        })
