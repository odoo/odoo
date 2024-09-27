# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import users
from odoo.addons.event_crm.tests.common import TestEventCrmCommon

class TestWebsiteEventCrmFlow(TestEventCrmCommon):

    @users('user_eventregistrationdesk')
    def test_visitor_language_propagation(self):
        """
        This test makes sure that visitor and its language are propagated to the lead when a lead is
        created through a lead generation rule.

        `_run_on_registration`, which creates the lead, is called at `event.registration` creation
        and does not need to be called manually.
        """
        test_lang_website = self.env['website'].sudo().create({
            'name': 'test lang website',
            'user_id': self.env.ref('base.user_admin').id,
            'language_ids': [self.env.ref('base.lang_en').id, self.env.ref('base.lang_fr').id]
        })
        test_lang_visitor = self.env['website.visitor'].sudo().create({
            'name': 'test visitor language',
            'lang_id': self.env.ref('base.lang_en').id,
            'access_token': 'f9d2ffa0427d4e4b1d740cf5eb3cdc20',
            'website_id': test_lang_website.id,
        })
        # 3 leads created w/ Lead Generation rules in TestEventCrmCommon: 1 per attendee and 1 per order
        test_lang_registration1, test_lang_registration2 = self.env['event.registration'].create([
            {
                'event_id': self.event_0.id,
                'visitor_id': test_lang_visitor.id,
                'email': 'test@test.example.com',
            },
            {
                'event_id': self.event_0.id,
                'visitor_id': test_lang_visitor.id,
                'email': 'test2@test.example.com',
            },
        ])
        leads = test_lang_registration1.sudo().lead_ids | test_lang_registration2.sudo().lead_ids
        self.assertEqual(leads.visitor_ids, test_lang_visitor)
        self.assertEqual(leads.lang_id, test_lang_visitor.lang_id)
