# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from mock import patch

from odoo.tests.common import TransactionCase


class TestPartnerAssign(TransactionCase):

    def setUp(self):
        super(TestPartnerAssign, self).setUp()

        def geo_find(addr, apikey):
            return {
                'Wavre, Belgium': (50.7158956, 4.6128075),
                'Cannon Hill Park, B46 3AG Birmingham, United Kingdom': (52.45216, -1.898578),
            }.get(addr)

        patcher = patch('odoo.addons.base_geolocalize.models.res_partner.geo_find', wraps=geo_find)
        patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('odoo.addons.website_crm_partner_assign.models.crm_lead.geo_find',
                        wraps=geo_find)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_00_partner_assign(self):
        partner2 = self.env.ref('base.res_partner_2')
        lead = self.env.ref('crm.crm_case_21')
        '''
            In order to test find nearest Partner functionality and assign to opportunity,
            I Set Geo Lattitude and Longitude according to partner address.
        '''
        partner2.geo_localize()

        # I check Geo Latitude and Longitude of partner after set
        self.assertTrue(50 < partner2.partner_latitude < 51, "Latitude is wrong: 50 < %s < 51" % partner2.partner_latitude)
        self.assertTrue(3 < partner2.partner_longitude < 5, "Longitude is wrong: 3 < %s < 5" % partner2.partner_longitude)

        # I assign nearest partner to opportunity.
        lead.assign_partner()

        # I check assigned partner of opportunity who is nearest Geo Latitude and Longitude of opportunity.
        self.assertEqual(lead.partner_assigned_id, self.env.ref('base.res_partner_18'), "Opportuniy is not assigned nearest partner")
        self.assertTrue(50 < lead.partner_latitude < 55, "Latitude is wrong: 50 < %s < 55" % lead.partner_latitude)
        self.assertTrue(-4 < lead.partner_longitude < -1, "Longitude is wrong: -4 < %s < -1" % lead.partner_longitude)

        # I forward this opportunity to its nearest partner.
        context = dict(self.env.context, default_model='crm.lead', default_res_id=lead.id, active_ids=lead.ids)
        lead_forwarded = self.env['crm.lead.forward.to.partner'].with_context(context).create({})
        try:
            lead_forwarded.action_forward()
        except:
            pass
