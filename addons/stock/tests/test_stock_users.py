# -*- coding: utf-8 -*-

from openerp.tests.common import TransactionCase

class TestUser(TransactionCase):
    def test_res_user(self):
        UserObj = self.env['res.users']
        res_users_stock_manager = UserObj.create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'Stock Manager',
            'login': 'sam',
            'email': 'stockmanager@yourcompany.com',
            'groups_id': [(4, self.env.ref('stock.group_stock_manager').id)]
            })

        res_users_stock_user = UserObj.create({
            'company_id': self.env.ref('base.main_company').id,
            'name': 'Stock User',
            'login': 'sau',
            'email': 'stockuser@yourcompany.com',
            'groups_id': [(4, self.env.ref('stock.group_stock_user').id)]
            })
        pass
