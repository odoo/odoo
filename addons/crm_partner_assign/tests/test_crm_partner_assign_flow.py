# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestCrmPartnerAssignFlow(common.TransactionCase):
    def setUp(self):
        super(TestCrmPartnerAssignFlow, self).setUp()
        self.partner_2 = self.env.ref('base.res_partner_2')
        self.crm_lead = self.env.ref('crm.crm_case_21')
        self.partner_18 = self.env.ref('base.res_partner_18')

    def test_00_crm_partner_assign_flow(self):

        # I Set Geo Lattitude and Longitude according to partner address.
        self.partner_2.geo_localize()

        # I check Geo Latitude and Longitude of partner after set
        self.assertGreater(self.partner_2.partner_latitude, 50,
                           "Latitude is wrong: 50 < %s" % self.partner_2.partner_latitude)
        self.assertLess(self.partner_2.partner_latitude, 51,
                        "Latitude is wrong: %s < 51" % self.partner_2.partner_latitude)
        self.assertGreater(self.partner_2.partner_longitude, 3,
                           "Longitude is wrong: 3 < %s" % self.partner_2.partner_longitude)
        self.assertLess(self.partner_2.partner_longitude, 5,
                        "Longitude is wrong: %s < 5" % self.partner_2.partner_longitude)

        # I assign nearest partner to opportunity.
        self.crm_lead.action_assign_partner()

        # I check assigned partner of opportunity who is nearest Geo Latitude
        # and Longitude of opportunity.
        self.assertEqual(self.crm_lead.partner_assigned_id, self.partner_18,
                         "Opportuniy is not assigned nearest partner")
        self.assertGreater(self.crm_lead.partner_latitude, 50,
                           "Latitude is wrong: 50 < %s" % self.crm_lead.partner_latitude)
        self.assertLess(self.crm_lead.partner_latitude, 55,
                        "Latitude is wrong: %s < 55" % self.crm_lead.partner_latitude)
        self.assertGreater(self.crm_lead.partner_longitude, -4,
                           "Longitude is wrong: -4 < %s" % self.crm_lead.partner_longitude)
        self.assertLess(self.crm_lead.partner_longitude, -1,
                        "Longitude is wrong: %s < -1" % self.crm_lead.partner_longitude)     
        # I forward this opportunity to its nearest partner.
        lead_forward_to_partner = self.env['crm.lead.forward.to.partner'].with_context(
            {'default_model': 'crm.lead',
             'default_res_id': self.ref('crm.crm_case_21'),
             'active_ids': [self.ref('crm.crm_case_21')]}).create({})
        try:
            lead_forward_to_partner.action_forward()
        except:
            pass