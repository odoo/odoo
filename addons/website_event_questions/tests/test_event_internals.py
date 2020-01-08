# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo.addons.website_event_questions.tests.common import TestEventQuestionCommon
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users


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
