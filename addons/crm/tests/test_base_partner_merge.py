# -*- coding: utf-8 -*-

from openerp.tests import common

class TestBasePartnerMerge(common.TransactionCase):

    def test_partner_merge(self):
        """ Tests for Merge Partner """
        BasePartnerMerge = self.env[
            'base.partner.merge.automatic.wizard']
        ResPartner = self.env['res.partner']

        partner_test_merge1 = ResPartner.create(
            dict(
                name="Armande Crm_User",
                city="Belgium",
                email="admin@openerp.com",
            ))

        partner_test_merge2 = ResPartner.create(
            dict(
                name="Armande Crm_User",
                city="Belgium",
                email="demo@openerp.com",
            ))

        base_partner = BasePartnerMerge.create(
            vals={'group_by_name': True})
        base_partner.start_process_cb()
        base_partner.merge_cb()
        partner_count = base_partner.dst_partner_id.search_count(
            [('name', 'ilike', 'Armande Crm_User')])
        self.assertEqual(
            partner_count, 1, 'Crm: Partners which name have same are not succesfully merged')
