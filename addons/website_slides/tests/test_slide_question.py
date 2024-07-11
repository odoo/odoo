# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command

from odoo.addons.website_slides.tests import common as slides_common
from odoo.tests.common import users

class TestSlideQuestionManagement(slides_common.SlidesCase):

    @users('user_officer')
    def test_compute_answers_validation_error(self):
        channel = self.env['slide.channel'].create({
            'name': 'Test compute answers channel',
            'slide_ids': [Command.create({
                'name': "Test compute answers validation error slide",
                'slide_category': 'quiz',
                'question_ids': [Command.create({
                    'question': 'Will test compute answers validation error pass?',
                    'answer_ids': [
                        Command.create({
                            'text_value': 'An incorrect answer',
                        }),
                        Command.create({
                            'is_correct': True,
                            'text_value': 'A correct answer',
                        })
                    ]
                })]
            })]
        })

        question = channel.slide_ids[0].question_ids[0]
        self.assertFalse(question.answers_validation_error)

        for val in (False, True):
            question.answer_ids[0].is_correct = val
            question.answer_ids[1].is_correct = val
            self.assertTrue(question.answers_validation_error)
