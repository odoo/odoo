# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event.tests.common import TestEventCommon
from odoo.fields import X2ManyCmd


class TestEventQuestionCommon(TestEventCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventQuestionCommon, cls).setUpClass()

        cls.event_question_1 = cls.env['event.question'].create({
            'title': 'Question1',
            'question_type': 'simple_choice',
            'event_type_id': cls.event_type_complex.id,
            'once_per_order': False,
            'answer_ids': [
                (X2ManyCmd.CREATE, 0, {'name': 'Q1-Answer1'}),
                (X2ManyCmd.CREATE, 0, {'name': 'Q1-Answer2'})
            ],
        })
        cls.event_question_2 = cls.env['event.question'].create({
            'title': 'Question2',
            'question_type': 'simple_choice',
            'event_type_id': cls.event_type_complex.id,
            'once_per_order': True,
            'answer_ids': [
                (X2ManyCmd.CREATE, 0, {'name': 'Q2-Answer1'}),
                (X2ManyCmd.CREATE, 0, {'name': 'Q2-Answer2'})
            ],
        })
        cls.event_question_3 = cls.env['event.question'].create({
            'title': 'Question3',
            'question_type': 'text_box',
            'event_type_id': cls.event_type_complex.id,
            'once_per_order': True,
        })
        cls.event_type_complex.write({'use_questions': True})
