# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestMrpMulticompany(common.TransactionCase):

    def setUp(self):
        super(TestMrpMulticompany, self).setUp()

        group_user = self.env.ref('base.group_user')
        group_stock_manager = self.env.ref('stock.group_stock_manager')
        company_2 = self.env.ref('stock.res_company_1')
        self.multicompany_user_id = self.env['res.users'].create({
            'name': 'multicomp',
            'login': 'multicomp',
            'groups_id': [(6, 0, [group_user.id, group_stock_manager.id])],
            'company_id': company_2.id,
            'company_ids': [(6, 0, [company_2.id])]
        })

    def test_00_multicompany_user(self):
        """check no error on getting default mrp.production values in multicompany setting"""
        StockLocation = self.env['stock.location'].sudo(self.multicompany_user_id)
        fields = ['location_src_id', 'location_dest_id']
        defaults = StockLocation.default_get(['location_id', 'location_dest_id', 'type'])
        for field in fields:
            if defaults.get(field):
                try:
                    StockLocation.check_access_rule([defaults[field]], 'read')
                except Exception, exc:
                    assert False, "unreadable location %s: %s" % (field, exc)
