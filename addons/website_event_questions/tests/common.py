# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import EventCase


class TestEventQuestionCommon(EventCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventQuestionCommon, cls).setUpClass()

        cls.event_type_questions = cls.env['event.type'].create({
            'name': 'Update Type',
            'auto_confirm': True,
            'has_seats_limitation': True,
            'seats_max': 30,
            'default_timezone': 'Europe/Paris',
            'event_type_ticket_ids': [],
            'event_type_mail_ids': [],
        })

        cls.event_question_1 = cls.env['event.question'].create({
            'title': 'Question1',
            'question_type': 'simple_choice',
            'event_type_id': cls.event_type_questions.id,
            'once_per_order': False,
            'answer_ids': [
                (0, 0, {'name': 'Q1-Answer1'}),
                (0, 0, {'name': 'Q1-Answer2'})
            ],
        })
        cls.event_question_2 = cls.env['event.question'].create({
            'title': 'Question2',
            'question_type': 'simple_choice',
            'event_type_id': cls.event_type_questions.id,
            'once_per_order': True,
            'answer_ids': [
                (0, 0, {'name': 'Q2-Answer1'}),
                (0, 0, {'name': 'Q2-Answer2'})
            ],
        })
        cls.event_question_3 = cls.env['event.question'].create({
            'title': 'Question3',
            'question_type': 'text_box',
            'event_type_id': cls.event_type_questions.id,
            'once_per_order': True,
        })
