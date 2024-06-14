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

    def test_copy_quiz_question(self):
        """Verify that the copy question method correctly copies a question record and its associated answers."""
        question = self.question_1
        # Copy the question record
        copied_question = question.copy()

        # Check that the new question has the same attributes as the original
        self.assertEqual(copied_question.question, question.question)
        self.assertEqual(copied_question.slide_id.id, question.slide_id.id)

        # Check that the answers have been copied correctly
        self.assertEqual(len(copied_question.answer_ids), 2)
        self.assertTrue(any(answer.text_value == "25' at 180°C" and answer.is_correct for answer in copied_question.answer_ids))
        self.assertTrue(any(answer.text_value == "Raw" and not answer.is_correct for answer in copied_question.answer_ids))
