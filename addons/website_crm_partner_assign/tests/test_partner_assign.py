# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_crm_partner_assign.controllers.main import (
    WebsiteAccount,
    WebsiteCrmPartnerAssign,
)


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
        self.startPatcher(patcher)

    def test_opportunity_count(self):
        self.customer_uk.write({
            'is_company': True,
            'child_ids': [
                (0, 0, {'name': 'Uk Children 1',
                       }),
                (0, 0, {'name': 'Uk Children 2',
                       }),
            ],
        })
        lead_uk_assigned = self.env['crm.lead'].create({
            'name': 'Office Design and Architecture',
            'partner_assigned_id': self.customer_uk.id,
            'type': 'opportunity',
        })
        children_leads = self.env['crm.lead'].create([
            {'name': 'Children 1 Lead 1',
             'partner_id': self.customer_uk.child_ids[0].id,
             'type': 'lead'},
            {'name': 'Children 1 Lead 2',
             'partner_id': self.customer_uk.child_ids[0].id,
             'type': 'lead'},
            {'name': 'Children 2 Lead 1',
             'partner_id': self.customer_uk.child_ids[1].id,
             'type': 'lead'},
            {'name': 'Children 2 Lead 2',
             'partner_id': self.customer_uk.child_ids[1].id,
             'type': 'lead'},
        ])
        children_leads_assigned = self.env['crm.lead'].create([
            {'name': 'Children 1 Lead 1',
             'partner_assigned_id': self.customer_uk.child_ids[0].id,
             'type': 'lead'},
            {'name': 'Children 1 Lead 2',
             'partner_assigned_id': self.customer_uk.child_ids[0].id,
             'type': 'lead'},
            {'name': 'Children 2 Lead 1',
             'partner_assigned_id': self.customer_uk.child_ids[1].id,
             'type': 'lead'},
            {'name': 'Children 2 Lead 2',
             'partner_assigned_id': self.customer_uk.child_ids[1].id,
             'type': 'lead'},
        ])

        self.assertEqual(
            repr(self.customer_uk.action_view_opportunity()['domain']),
            repr([('id', 'in', sorted(self.lead_uk.ids + lead_uk_assigned.ids + children_leads.ids))]),
            'Parent: own + children leads + assigned'
        )
        self.assertEqual(
            repr(self.customer_uk.child_ids[0].action_view_opportunity()['domain']),
            repr([('id', 'in', sorted(children_leads[0:2].ids + children_leads_assigned[0:2].ids))]),
            'Children: own leads + assigned'
        )
        self.assertEqual(
            repr(self.customer_uk.child_ids[1].action_view_opportunity()['domain']),
            repr([('id', 'in', sorted(children_leads[2:].ids + children_leads_assigned[2:].ids))]),
            'Children: own leads + assigned'
        )

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
        # YTI Note: We should probably mock the call
        partner_be.with_context(force_geo_localize=True).geo_localize()

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
            notification_type='email',
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
        record_action = self.lead_portal._get_access_action(access_uid=self.user_portal.id)
        self.assertEqual(record_action['url'], '/my/opportunity/%s' % self.lead_portal.id)
        self.assertEqual(record_action['type'], 'ir.actions.act_url')

    def test_route_portal_my_opportunities_as_portal(self):
        """Test that the portal user can access its own opportunities even if
        does not have access to the 'activity_date_deadline' field (needed
        if using filter 'Today Activities' or 'Overdue Activities')."""

        lead_today = self.lead_portal
        lead_yesterday = self.lead_portal.copy()

        (lead_today | lead_yesterday).type = "opportunity"

        lead_today.activity_schedule("crm.lead_test_activity_1", date.today())
        lead_yesterday.activity_schedule(
            "crm.lead_test_activity_1", date.today() - timedelta(days=1)
        )

        def render_function(_, values, *args, **kwargs):
            self.assertIn(
                lead_today,
                values["opportunities"],
                "Lead with today scheduled activity should be in filtered opportunities.",
            )
            self.assertNotIn(
                lead_yesterday,
                values["opportunities"],
                "Lead with yesterday scheduled activity should not be in filtered opportunities.",
            )

        with self.with_user(self.user_portal.login), MockRequest(
            self.env, website=self.env["website"].browse(1)
        ) as mock_request:
            mock_request.render = render_function
            WebsiteAccount().portal_my_opportunities(filterby="today")

    @patch('odoo.http.GeoIP')
    def test_03_crm_partner_assign_geolocalization(self, GeoIpMock):
        """
            This test checks situation when "{OdooURL}/partners" is visited from foreign country without resellers.
            It uses Mexico as an example.

            Why patching of GeoIP is used?
            Tested function (WebsiteCrmPartnerAssign.partners) uses GeoIp.country_code which is read_only, because
            of the property decorator https://docs.python.org/3/library/functions.html#property
            Patching is allowing to modify normally read_only value.
        """
        # Patch GeoIp so it acts, as if Odoo client is located in Mexico
        GeoIpMock.return_value.country_code = 'MX'

        # Create a partner outside of Mexico
        non_mexican_partner = self.env['res.partner'].create({
            'name': 'Non_Mexican_Partner',
            'is_company': True,
            'grade_id': self.env['res.partner.grade'].search([], limit=1).id,
            'website_published': True,
            'country_id': self.env['res.country'].search([('code', '!=', 'mx')], limit=1).id
        })

        def render_function(_, values, *args, **kwargs):
            """ Tests values at the end of WebsiteCrmPartnerAssign.partners method."""
            self.assertIn("partners", values, "Partner key is not present in the values, can't perform subsequent checks.")
            self.assertIn(non_mexican_partner, values['partners'], "Non-Mexican Partner is not present when rendering partners from Mexico; fallback protection (protecting from no results) didn't work.")
            return 'rendered'

        with MockRequest(self.env, website=self.env['website'].browse(1)) as mock_request:
            mock_request.render = render_function
            res = WebsiteCrmPartnerAssign().partners()
            self.assertEqual([b'rendered'], res.response, "render_function wasn't called")
