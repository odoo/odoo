# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.crm.tests.test_crm_lead_merge import TestLeadMergeCommon
from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.tests.common import tagged, users


@tagged('lead_manage')
class TestLeadCrmMerge(TestLeadMergeCommon, TestEventCrmCommon):

    @users('user_sales_manager')
    def test_merge_method_dependencies(self):
        """ Test if dependences for leads are not lost while merging leads. In
        this test leads are ordered as

        lead_w_contact -----------lead---seq=30
        lead_w_email -------------lead---seq=3
        lead_1 -------------------lead---seq=1
        lead_w_partner_company ---lead---seq=1----------------registrations
        lead_w_partner -----------lead---seq=False
        """
        TestLeadMergeCommon.merge_fields.append('registration_ids')

        registration = self.env['event.registration'].sudo().create({
            'partner_id': self.event_customer.id,
            'event_id': self.event_0.id,
            'lead_ids': [(4, self.lead_w_partner_company.id)],
        })
        self.assertEqual(self.lead_w_partner_company.registration_ids, registration)

        leads = self.env['crm.lead'].browse(self.leads.ids)._sort_by_confidence_level(reverse=True)
        with self.assertLeadMerged(self.lead_w_contact, leads,
                                   name=self.lead_w_contact.name,
                                   registration_ids=registration
                                   ):
            leads._merge_opportunity(auto_unlink=False, max_length=None)
