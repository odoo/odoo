# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.tests import common


class TestCrmPartnerAssignFlow(common.TransactionCase):

    def test_00_crm_partner_assignflow(self):

        Partner_2 = self.env.ref('base.res_partner_2')
        Partner_2.geo_localize()

        # I check Geo Latitude and Longitude of partner after set
        self.assertGreater(Partner_2.partner_latitude, 50,
                           "Latitude is wrong: 50 < %s" % Partner_2.partner_latitude)
        self.assertLess(Partner_2.partner_latitude, 51,
                        "Latitude is wrong: %s < 51" % Partner_2.partner_latitude)

        self.assertGreater(Partner_2.partner_longitude, 3,
                           "Longitude is wrong: 3 < %s" % Partner_2.partner_longitude)
        self.assertLess(Partner_2.partner_longitude, 5,
                        "Longitude is wrong: %s < 5" % Partner_2.partner_longitude)

        # I assign nearest partner to opportunity.
        CrmLead = self.env.ref('crm.crm_case_19')
        CrmLead.action_assign_partner()

        # I check assigned partner of opportunity who is nearest Geo Latitude
        # and Longitude of opportunity.
        Partner_15 = self.env.ref('base.res_partner_15')
        self.assertEqual(CrmLead.partner_assigned_id, Partner_15,
                         "Opportuniy is not assigned nearest partner")

        self.assertGreater(CrmLead.partner_latitude, 50,
                           "Latitude is wrong: 50 < %s" % CrmLead.partner_latitude)
        self.assertLess(CrmLead.partner_latitude, 55,
                        "Latitude is wrong: %s < 55" % CrmLead.partner_latitude)

        self.assertGreater(CrmLead.partner_longitude, -4,
                           "Longitude is wrong: -4 < %s" % CrmLead.partner_longitude)
        self.assertLess(CrmLead.partner_longitude, -1,
                        "Longitude is wrong: %s < -1" % CrmLead.partner_longitude)

        # I forward this opportunity to its nearest partner.
        lead_forward_to_partner = self.env['crm.lead.forward.to.partner'].with_context(
            {'default_model': 'crm.lead',
             'default_res_id': self.env.ref('crm.crm_case_19').id,
             'active_ids': [self.env.ref('crm.crm_case_19').id]}).create({})

        try:
            lead_forward_to_partner.action_forward()
        except:
            pass
