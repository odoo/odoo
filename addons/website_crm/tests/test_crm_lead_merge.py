# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.test_crm_lead_merge import TestLeadMergeCommon
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadVisitorMerge(TestLeadMergeCommon):

    @users('user_sales_manager')
    def test_merge_method_dependencies(self):
        """ Test if dependences for leads are not lost while merging leads. In
        this test leads are ordered as

        lead_w_contact -----------lead---seq=30
        lead_w_email -------------lead---seq=3
        lead_1 -------------------lead---seq=1
        lead_w_partner_company ---lead---seq=1----------------visitor
        lead_w_partner -----------lead---seq=False------------visitor
        """
        TestLeadMergeCommon.merge_fields.append('visitor_ids')

        visitors = self.env['website.visitor'].sudo().create([
            {
                'access_token': 'f9d2ffa0427d4e4b1d740cf5eb3cdc20',
                'lead_ids': [(4, self.lead_w_partner_company.id)],
            },
            {
                'access_token': 'f9d2c3f741a79200487728eac989e678',
                'lead_ids': [(4, self.lead_w_partner.id)],
            }
        ])
        self.assertEqual(self.lead_w_partner_company.visitor_ids, visitors[0])
        self.assertEqual(self.lead_w_partner.visitor_ids, visitors[1])

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)
        with self.assertLeadMerged(self.lead_w_contact, leads,
                                   name=self.lead_w_contact.name,
                                   visitor_ids=visitors
                                   ):
            leads._merge_opportunity(auto_unlink=False, max_length=None)
