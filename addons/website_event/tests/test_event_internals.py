# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.addons.event.tests.common import EventCase


class TestEventData(EventCase, MockVisitor):

    @classmethod
    def setUpClass(cls):
        super(TestEventData, cls).setUpClass()
        cls.event_public, cls.event_link_only, cls.event_logged_users = cls.env['event.event'].sudo().create([{
            'name': 'event',
            'website_visibility': website_visibility,
            'website_published': True,
        } for website_visibility in ['public', 'link', 'logged_users']])
        cls.events_visibility_test = cls.event_public | cls.event_link_only | cls.event_logged_users

    def test_registration_answer_search(self):
        """ Test our custom name_search implementation in 'event.registration.answer'.
        We search on both the 'value_answer_id' and 'value_text_box' fields to allow users to easily
        filter registrations based on the selected answers of the attendees. """

        event = self.env['event.event'].create({
            'name': 'Test Event',
            'event_type_id': self.event_type_questions.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })

        [registration_1, registration_2, registration_3] = self.env['event.registration'].create([{
            'event_id': event.id,
            'partner_id': self.env.user.partner_id.id,
            'registration_answer_ids': [
                (0, 0, {
                    'question_id': self.event_question_1.id,
                    'value_answer_id': self.event_question_1.answer_ids[0].id,
                }),
            ]
        }, {
            'event_id': event.id,
            'partner_id': self.env.user.partner_id.id,
            'registration_answer_ids': [
                (0, 0, {
                    'question_id': self.event_question_1.id,
                    'value_answer_id': self.event_question_1.answer_ids[1].id,
                }),
                (0, 0, {
                    'question_id': self.event_question_3.id,
                    'value_text_box': "My Answer",
                }),
            ]
        }, {
            'event_id': event.id,
            'partner_id': self.env.user.partner_id.id,
            'registration_answer_ids': [
                (0, 0, {
                    'question_id': self.event_question_3.id,
                    'value_text_box': "Answer2",
                }),
            ]
        }])

        search_res = self.env['event.registration'].search([
            ('registration_answer_ids', 'ilike', 'Answer1')
        ])
        # should fetch "registration_1" because the answer to the first question is "Q1-Answer1"
        self.assertEqual(search_res, registration_1)

        search_res = self.env['event.registration'].search([
            ('registration_answer_ids', 'ilike', 'Answer2')
        ])
        # should fetch "registration_2" because the answer to the first question is "Q1-Answer2"
        # should fetch "registration_3" because the answer to the third question is "Answer2" (as free text)
        self.assertEqual(search_res, registration_2 | registration_3)

    @users('user_employee')
    def test_website_visibility_internal_user(self):
        """ Check website visibility value for an internal user """
        visible_events = self.env['event.event'].search([
            ('id', 'in', self.events_visibility_test.ids),
            ('is_visible_on_website', '=', True)])
        self.assertIn(self.event_public, visible_events)
        self.assertNotIn(self.event_link_only, visible_events)
        self.assertIn(self.event_logged_users, visible_events)

    @users('portal_test')
    def test_website_visibility_portal_user(self):
        """ Check website visibility value for a portal user """
        visible_events = self.env['event.event'].search([
            ('id', 'in', self.events_visibility_test.ids),
            ('is_visible_on_website', '=', True)])
        self.assertIn(self.event_public, visible_events)
        self.assertNotIn(self.event_link_only, visible_events)
        self.assertIn(self.event_logged_users, visible_events)

    @users('public_test')
    def test_website_visibility_public_user(self):
        """ Check website visibility value for public user """
        visible_events = self.env['event.event'].search([
            ('id', 'in', self.events_visibility_test.ids),
            ('is_visible_on_website', '=', True)])
        self.assertIn(self.event_public, visible_events)
        self.assertNotIn(self.event_link_only, visible_events)
        self.assertNotIn(self.event_logged_users, visible_events)

        # Check that a visitor can see event where he is participating
        website_visitor = self.env['website.visitor'].sudo().create({
            "name": 'Website Visitor',
            "access_token": 'c8d20bd006c3bf46b875451defb5991d'
        })
        self.env['event.registration'].sudo().create({
            'name': "Registration from visitor",
            'event_id': self.event_link_only.id,
            'visitor_id': website_visitor.id,
        })
        with self.mock_visitor_from_request(force_visitor=website_visitor):
            visible_events = self.env['event.event'].search([
                ('id', 'in', self.events_visibility_test.ids),
                ('is_visible_on_website', '=', True)])
            self.assertIn(self.event_public, visible_events)
            self.assertIn(self.event_link_only, visible_events, "Should now be visible because visitor is participating")
            self.assertNotIn(self.event_logged_users, visible_events)
