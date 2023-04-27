# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user


class TestPartnerAssign(TransactionCase):

    def setUp(self):
        super(TestPartnerAssign, self).setUp()

        self.customer_uk = self.env['res.partner'].create({
            'name': 'Nigel',
            'country_id': self.env.ref('base.uk').id,
            'city': 'Birmingham',
            'zip': 'B46 3AG',
            'street': 'Cannon Hill Park',
        })
        self.lead_uk = self.env['crm.lead'].create({
            'type': 'opportunity',
            'name': 'Office Design and Architecture',
            'partner_id': self.customer_uk.id
        })

        def geo_find(addr, **kw):
            return {
                'Wavre, Belgium': (50.7158956, 4.6128075),
                'Cannon Hill Park, B46 3AG Birmingham, United Kingdom': (52.45216, -1.898578),
            }.get(addr)

        patcher = patch('odoo.addons.base_geolocalize.models.base_geocoder.GeoCoder.geo_find', wraps=geo_find)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_partner_assign(self):
        """ Test the automatic assignation using geolocalisation """
        partner_be = self.env['res.partner'].create({
            "name": "Agrolait",
            "is_company": True,
            "city": "Wavre",
            "zip": "1300",
            "country_id": self.env.ref("base.be").id,
            "street": "69 rue de Namur",
            "partner_weight": 10,
        })
        partner_uk = self.env['res.partner'].create({
            "name": "Think Big Systems",
            "is_company": True,
            "city": "London",
            "country_id": self.env.ref("base.uk").id,
            "street": "89 Lingfield Tower",
            "partner_weight": 10,
        })

        lead = self.lead_uk

        # In order to test find nearest Partner functionality and assign to opportunity,
        # I Set Geo Lattitude and Longitude according to partner address.
        partner_be.geo_localize()

        # I check Geo Latitude and Longitude of partner after set
        self.assertTrue(50 < partner_be.partner_latitude < 51, "Latitude is wrong: 50 < %s < 51" % partner_be.partner_latitude)
        self.assertTrue(3 < partner_be.partner_longitude < 5, "Longitude is wrong: 3 < %s < 5" % partner_be.partner_longitude)

        # I assign nearest partner to opportunity.
        lead.assign_partner()

        # I check assigned partner of opportunity who is nearest Geo Latitude and Longitude of opportunity.
        self.assertEqual(lead.partner_assigned_id, partner_uk, "Opportuniy is not assigned nearest partner")
        self.assertTrue(50 < lead.partner_latitude < 55, "Latitude is wrong: 50 < %s < 55" % lead.partner_latitude)
        self.assertTrue(-4 < lead.partner_longitude < -1, "Longitude is wrong: -4 < %s < -1" % lead.partner_longitude)
        self.assertTrue(lead.date_partner_assign, "Partner Assignment Date should be set")

        # I forward this opportunity to its nearest partner.
        context = dict(self.env.context, default_model='crm.lead', default_res_id=lead.id, active_ids=lead.ids)
        lead_forwarded = self.env['crm.lead.forward.to.partner'].with_context(context).create({})
        try:
            lead_forwarded.action_forward()
        except:
            pass


class TestPartnerLeadPortal(TestCrmCommon):

    def setUp(self):
        super(TestPartnerLeadPortal, self).setUp()
        # Partner Grade
        self.grade = self.env['res.partner.grade'].create({
            'name': "Grade Test",
            'partner_weight': 42,
            'sequence': 3,
        })
        # Integrating user/partner, having a salesman
        self.user_portal = mail_new_test_user(
            self.env, login='user_portal',
            name='Patrick Portal', email='portal@test.example.com',
            company_id=self.env.ref("base.main_company").id,
            grade_id=self.grade.id,
            user_id=self.user_sales_manager.id,
            notification_type='inbox',
            groups='base.group_portal',
        )

        # New lead, assigned to the new portal
        self.lead_portal = self.env['crm.lead'].with_context(mail_notrack=True).create({
            'type': "lead",
            'name': "Test lead new",
            'user_id': False,
            'team_id': False,
            'description': "This is the description of the test new lead.",
            'partner_assigned_id': self.user_portal.partner_id.id
        })

    def test_partner_lead_accept(self):
        """ Test an integrating partner accepting the lead """
        self.lead_portal.with_user(self.user_portal).partner_interested(comment="Oh yeah, I take that lead !")
        self.assertEqual(self.lead_portal.type, 'opportunity')

    def test_partner_lead_decline(self):
        """ Test an integrating partner decline the lead """
        self.lead_portal.with_user(self.user_portal).partner_desinterested(comment="No thanks, I have enough leads !", contacted=True, spam=False)

        self.assertFalse(self.lead_portal.partner_assigned_id.id, 'The partner_assigned_id of the declined lead should be False.')
        self.assertTrue(self.user_portal.partner_id in self.lead_portal.sudo().partner_declined_ids, 'Partner who has declined the lead should be in the declined_partner_ids.')

    def test_lead_access_right(self):
        """ Test another portal user can not write on every leads """
        # portal user having no right
        poor_portal_user = self.env['res.users'].with_context({'no_reset_password': True, 'mail_notrack': True}).create({
            'name': 'Poor Partner (not integrating one)',
            'email': 'poor.partner@ododo.com',
            'login': 'poorpartner',
            'groups_id': [(6, 0, [self.env.ref('base.group_portal').id])],
        })
        # try to accept a lead that is not mine
        with self.assertRaises(AccessError):
            self.lead_portal.with_user(poor_portal_user).partner_interested(comment="Oh yeah, I take that lead !")

    def test_lead_creation(self):
        """ Test the opportinuty creation from portal """
        data = self.env['crm.lead'].with_user(self.user_portal).create_opp_portal({
            'title': "L'ours bleu",
            'description': 'A good joke',
            'contact_name': 'Renaud Rutten',
        })
        opportunity = self.env['crm.lead'].browse(data['id'])
        salesmanteam = self.env['crm.team']._get_default_team_id(user_id=self.user_portal.user_id.id)

        self.assertEqual(opportunity.team_id, salesmanteam, 'The created opportunity should have the same team as the salesman default team of the opportunity creator.')
        self.assertEqual(opportunity.partner_assigned_id, self.user_portal.partner_id, 'Assigned Partner of created opportunity is the (portal) creator.')

    def test_portal_mixin_url(self):
        record_action = self.lead_portal.get_access_action(self.user_portal.id)
        self.assertEqual(record_action['url'], '/my/opportunity/%s' % self.lead_portal.id)
        self.assertEqual(record_action['type'], 'ir.actions.act_url')
