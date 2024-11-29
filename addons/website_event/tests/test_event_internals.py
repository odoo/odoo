# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_event.controllers.main import WebsiteEventController
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

    def test_process_attendees_form(self):
        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': self.event_type_questions.with_user(self.env.user).id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })
        ticket_id_1 = self.env['event.event.ticket'].create([{
            'name': 'Regular',
            'event_id': event.id,
            'seats_max': 200,
        }])
        ticket_id_2 = self.env['event.event.ticket'].create([{
            'name': 'VIP',
            'event_id': event.id,
            'seats_max': 200,
        }])

        [name_question, email_question, phone_question] = event.question_ids.filtered(
            lambda q: q.question_type in ('name', 'email', 'phone', 'company_name'))

        [second_phone_question, company_name_question] = self.env['event.question'].create([{
            'title': 'Second Phone',
            'question_type': 'phone',
            'event_id': event.id,
        }, {
            'title': 'Company Name',
            'question_type': 'company_name',
            'event_id': event.id,
        }])

        form_details = {
            '1-name-%s' % name_question.id: 'Pixis',
            '1-email-%s' % email_question.id: 'pixis@gmail.com',
            '1-phone-%s' % phone_question.id: '+32444444444',
            '1-phone-%s' % second_phone_question.id: '+32555555555',
            '1-event_ticket_id': ticket_id_1.id,
            '2-name-%s' % name_question.id: 'Geluchat',
            '2-email-%s' % email_question.id: 'geluchat@gmail.com',
            '2-phone-%s' % phone_question.id: '+32777777777',
            '2-company_name-%s' % company_name_question.id: 'My Company',
            '2-event_ticket_id': ticket_id_2.id,
            '1-simple_choice-%s' % self.event_question_1.id: '5',
            '2-simple_choice-%s' % self.event_question_1.id: '9',
            '0-simple_choice-%s' % self.event_question_2.id: '7',
            '0-text_box-%s' % self.event_question_3.id: 'Free Text',
        }

        with MockRequest(self.env):
            registrations = WebsiteEventController()._process_attendees_form(event, form_details)

        self.assertEqual(registrations, [
            {'name': 'Pixis', 'email': 'pixis@gmail.com', 'phone': '+32444444444', 'event_ticket_id': ticket_id_1.id,
            'registration_answer_ids': [
                (0, 0, {'question_id': name_question.id, 'value_text_box': 'Pixis'}),
                (0, 0, {'question_id': email_question.id, 'value_text_box': 'pixis@gmail.com'}),
                (0, 0, {'question_id': phone_question.id, 'value_text_box': '+32444444444'}),
                (0, 0, {'question_id': second_phone_question.id, 'value_text_box': '+32555555555'}),
                (0, 0, {'question_id': self.event_question_1.id, 'value_answer_id': 5}),
                (0, 0, {'question_id': self.event_question_2.id, 'value_answer_id': 7}),
                (0, 0, {'question_id': self.event_question_3.id, 'value_text_box': 'Free Text'})]},
            {'name': 'Geluchat', 'email': 'geluchat@gmail.com', 'phone': '+32777777777', 'company_name': 'My Company',
            'event_ticket_id': ticket_id_2.id,
            'registration_answer_ids': [
                (0, 0, {'question_id': name_question.id, 'value_text_box': 'Geluchat'}),
                (0, 0, {'question_id': email_question.id, 'value_text_box': 'geluchat@gmail.com'}),
                (0, 0, {'question_id': phone_question.id, 'value_text_box': '+32777777777'}),
                (0, 0, {'question_id': company_name_question.id, 'value_text_box': 'My Company'}),
                (0, 0, {'question_id': self.event_question_1.id, 'value_answer_id': 9}),
                (0, 0, {'question_id': self.event_question_2.id, 'value_answer_id': 7}),
                (0, 0, {'question_id': self.event_question_3.id, 'value_text_box': 'Free Text'})]}
        ])

    def test_process_attendees_form_no_tickets(self):
        """Check that registering with no ticket works."""
        event = self.env['event.event'].create({
            'name': 'Test Event',
            'event_type_id': self.event_type_questions.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })

        name_question, email_question = event.question_ids.filtered(
            lambda q: q.question_type in ('name', 'email'))

        form_details = {
            '1-name-%s' % name_question.id: 'Attendee Name',
            '1-email-%s' % email_question.id: 'attendee@example.com',
            '1-event_ticket_id': '0',
        }

        with MockRequest(self.env):
            registrations = WebsiteEventController()._process_attendees_form(event, form_details)

        self.assertEqual(len(registrations), 1)
        self.assertDictEqual(registrations[0], {
            'name': 'Attendee Name',
            'email': 'attendee@example.com',
            'event_ticket_id': False,
            'registration_answer_ids': [
                (0, 0, {'question_id': name_question.id, 'value_text_box': 'Attendee Name'}),
                (0, 0, {'question_id': email_question.id, 'value_text_box': 'attendee@example.com'})
            ]
        })
        self.assertTrue(registrations[0]['event_ticket_id'] is False,
                        f'Falsy string ids should be False, not {registrations[0]["event_ticket_id"]}')

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
