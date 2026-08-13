# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.crm.tests.common import TestCrmCommon
from odoo.addons.website.tests.test_website_visitor import WebsiteVisitorTestsCommon
from odoo.tests import tagged
from odoo.tests.common import users


@tagged('website_visitor', 'is_query_count')
class TestWebsiteVisitor(TestCrmCommon, WebsiteVisitorTestsCommon):

    def setUp(self):
        super(TestWebsiteVisitor, self).setUp()
        self.test_partner = self.env['res.partner'].create({
            'name': 'Test Customer',
            'email': '"Test Customer" <test@test.example.com>',
            'country_id': self.env.ref('base.be').id,
            'mobile': '+32456001122'
        })

    @users('user_sales_manager')
    def test_compute_email_phone(self):
        visitor_sudo = self.env['website.visitor'].sudo().create({
            'access_token': 'f9d2c6f3b024320ac31248595ac7fcb6',
        })
        visitor = visitor_sudo.with_user(self.env.user)  # as of 13.0 salesmen cannot create visitors, only read them
        customer = self.test_partner.with_user(self.env.user)
        self.assertFalse(visitor.email)
        self.assertFalse(visitor.mobile)

        # partner information copied on visitor -> behaves like related
        visitor_sudo.write({'partner_id': self.test_partner.id})
        self.assertEqual(visitor.email, customer.email_normalized)
        self.assertEqual(visitor.mobile, customer.mobile)

        # if reset -> behaves like a related, also reset on visitor
        visitor_sudo.write({'partner_id': False})
        self.assertFalse(visitor.email)
        self.assertFalse(visitor.mobile)

        # first lead created -> updates email
        lead_1 = self.env['crm.lead'].create({
            'name': 'Test Lead 1',
            'email_from': 'Rambeau Fort <beaufort@test.example.com',
            'visitor_ids': [(4, visitor.id)],
        })
        self.assertEqual(visitor.email, lead_1.email_normalized)
        self.assertFalse(visitor.mobile)

        # second lead created -> keep first email but takes mobile as not defined before
        lead_2 = self.env['crm.lead'].create({
            'name': 'Test Lead 1',
            'email_from': 'Martino Brie <brie@test.example.com',
            'country_id': self.env.ref('base.be').id,
            'mobile': '+32456001122',
            'visitor_ids': [(4, visitor.id)],
        })
        self.assertEqual(visitor.email, lead_1.email_normalized)
        self.assertEqual(visitor.mobile, lead_2.mobile)

        # partner win on leads
        visitor_sudo.write({'partner_id': self.test_partner.id})
        self.assertEqual(visitor.email, customer.email_normalized)
        self.assertEqual(visitor.mobile, customer.mobile)

        # partner updated -> fallback on leads
        customer.write({'mobile': False})
        self.assertEqual(visitor.email, customer.email_normalized)
        self.assertEqual(visitor.mobile, lead_2.mobile)

    def test_clean_inactive_visitors_crm(self):
        """ Visitors attached to leads should not be deleted even if not connected recently. """
        active_visitors = self.env['website.visitor'].create([{
            'lang_id': self.env.ref('base.lang_en').id,
            'country_id': self.env.ref('base.be').id,
            'website_id': 1,
            'last_connection_datetime': datetime.now() - timedelta(days=8),
            'access_token': 'f9d28aad05ebee0bca215837b129aa00',
            'lead_ids': [(0, 0, {
                'name': 'Lead Carl'
            })]
        }])

        self._test_unlink_old_visitors(self.env['website.visitor'], active_visitors)

    def test_link_to_visitor_crm(self):
        """ Same as parent's 'test_link_to_visitor' except we also test that leads
        are merged into main visitor. """
        [main_visitor, linked_visitor] = self.env['website.visitor'].create([
            self._prepare_main_visitor_data(),
            self._prepare_linked_visitor_data()
        ])
        all_leads = (main_visitor + linked_visitor).lead_ids
        linked_visitor._merge_visitor(main_visitor)

        self.assertVisitorDeactivated(linked_visitor, main_visitor)

        # leads of both visitors should be merged into main one
        self.assertEqual(len(main_visitor.lead_ids), 2)
        self.assertEqual(main_visitor.lead_ids, all_leads)
        for lead in all_leads:
            self.assertEqual(lead.visitor_ids, main_visitor)

    def _prepare_main_visitor_data(self):
        values = super()._prepare_main_visitor_data()
        values.update({
            'lead_ids': [(0, 0, {
                'name': 'Mitchel Main Lead'
            })]
        })
        return values

    def _prepare_linked_visitor_data(self):
        values = super()._prepare_linked_visitor_data()
        values.update({
            'lead_ids': [(0, 0, {
                'name': 'Mitchel Secondary Lead'
            })]
        })
        return values
