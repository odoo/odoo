# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestMrpMulticompany(common.TransactionCase):

    def setUp(self):
        super(TestMrpMulticompany, self).setUp()
        cr, uid = self.cr, self.uid

        # Usefull models
        self.ir_model_data = self.registry('ir.model.data')
        self.res_users = self.registry('res.users')
        self.stock_location = self.registry('stock.location')

        group_user_id = self.registry('ir.model.data').xmlid_to_res_id(cr, uid, 'base.group_user')
        group_stock_manager_id = self.registry('ir.model.data').xmlid_to_res_id(cr, uid, 'stock.group_stock_manager')
        company_2_id = self.registry('ir.model.data').xmlid_to_res_id(cr, uid, 'stock.res_company_1')
        self.multicompany_user_id = self.res_users.create(cr, uid,
            {'name': 'multicomp', 'login': 'multicomp',
             'groups_id': [(6, 0, [group_user_id, group_stock_manager_id])],
             'company_id': company_2_id, 'company_ids': [(6,0,[company_2_id])]})


    def test_00_multicompany_user(self):
        """check no error on getting default mrp.production values in multicompany setting"""
        cr, uid, context = self.cr, self.multicompany_user_id, {}
        fields = ['location_src_id', 'location_dest_id']
        defaults = self.stock_location.default_get(cr, uid, ['location_id', 'location_dest_id', 'type'], context)
        for field in fields:
            if defaults.get(field):
                try:
                    self.stock_location.check_access_rule(cr, uid, [defaults[field]], 'read', context)
                except Exception, exc:
                    assert False, "unreadable location %s: %s" % (field, exc)
