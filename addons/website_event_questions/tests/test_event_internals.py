# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_event_questions.controllers.main import WebsiteEvent
from odoo.addons.website_event_questions.tests.common import TestEventQuestionCommon


class TestEventData(TestEventQuestionCommon):

    @users('user_eventmanager')
    def test_event_type_configuration(self):
        event_type = self.event_type_complex.with_user(self.env.user)

        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': event_type.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })
        event._onchange_type()
        self.assertEqual(event.specific_question_ids.title, 'Question1')
        self.assertEqual(
            set(event.specific_question_ids.mapped('answer_ids.name')),
            set(['Q1-Answer1', 'Q1-Answer2']))
        self.assertEqual(event.general_question_ids.title, 'Question2')
        self.assertEqual(
            set(event.general_question_ids.mapped('answer_ids.name')),
            set(['Q2-Answer1', 'Q2-Answer2']))

    def test_process_attendees_form(self):
        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': self.event_type_complex.with_user(self.env.user).id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })

        form_details = {
            '1-name': 'Pixis',
            '1-email': 'pixis@gmail.com',
            '1-phone': '+32444444444',
            '1-event_ticket_id': '2',
            '1-answer_ids-8': '5',
            '2-name': 'Geluchat',
            '2-email': 'geluchat@gmail.com',
            '2-phone': '+32777777777',
            '2-event_ticket_id': '3',
            '2-answer_ids-8': '9',
            '0-answer_ids-3': '7',
            '0-answer_ids-4': '1',
        }

        with MockRequest(self.env):
            registrations = WebsiteEvent()._process_attendees_form(event, form_details)

        self.assertEqual(registrations, [
            {'name': 'Pixis', 'email': 'pixis@gmail.com', 'phone': '+32444444444', 'event_ticket_id': 2, 'answer_ids': [[4, 5], [4, 7], [4, 1]]},
            {'name': 'Geluchat', 'email': 'geluchat@gmail.com', 'phone': '+32777777777', 'event_ticket_id': 3, 'answer_ids': [[4, 9], [4, 7], [4, 1]]}
        ])
