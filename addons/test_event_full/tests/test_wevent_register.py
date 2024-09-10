# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time

from odoo import tests
from odoo.addons.test_event_full.tests.common import TestWEventCommon


@tests.common.tagged('event_online', 'post_install', '-at_install')
class TestWEventRegister(TestWEventCommon):

    def test_event_update_lead(self):
        """Make sure that we update leads without issues when question's answer is added to an event attendee."""
        self.env['event.lead.rule'].create({
            'name': 'test_event_lead_rule',
            'lead_creation_basis': 'attendee',
            'lead_creation_trigger': 'create',
            'event_registration_filter': [['partner_id', '!=', False]],
            'lead_type': 'lead',
        })
        event_registration = self.env['event.registration'].create({
                    'name': 'Event Registration without answers added at first',
                    'event_id': self.event.id,
                    'partner_id': self.event_customer.id,
        })
        answer_string = 'Attendee Answer'
        event_registration.write({
            'registration_answer_ids': [(0, 0, {
                'question_id': self.event_question_2.id,
                'value_text_box': answer_string,
            })]
        })
        self.assertIn(answer_string, event_registration.lead_ids.description,
            "lead description not updated with the answer to the question")

    def test_register(self):
        with freeze_time(self.reference_now, tick=True):
            self.browser_js(
                '/event',
                'odoo.__DEBUG__.services["web_tour.tour"].run("wevent_register")',
                'odoo.__DEBUG__.services["web_tour.tour"].tours.wevent_register.ready',
                login=None
            )
        new_registrations = self.event.registration_ids
        visitor = new_registrations.visitor_id

        # check registration content
        self.assertEqual(len(new_registrations), 2)
        self.assertEqual(
            set(new_registrations.mapped("name")),
            set(["Raoulette Poiluchette", "Michel Tractopelle"])
        )
        self.assertEqual(
            set(new_registrations.mapped("phone")),
            set(["0456112233", "0456332211"])
        )
        self.assertEqual(
            set(new_registrations.mapped("email")),
            set(["raoulette@example.com", "michel@example.com"])
        )

        # check visitor stored information
        self.assertEqual(visitor.display_name, "Raoulette Poiluchette")
        self.assertEqual(visitor.event_registration_ids, new_registrations)
        self.assertEqual(visitor.partner_id, self.env['res.partner'])
        self.assertEqual(visitor.mobile, "0456112233")
        self.assertEqual(visitor.email, "raoulette@example.com")
