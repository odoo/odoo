# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class TestSurveyRandomize(TransactionCase):
    def test_01_generate_randomized_questions(self):
        """ Use random generate for a survey and verify that questions within the page are selected accordingly """
        Question = self.env['survey.question'].sudo()
        question_and_pages = self.env['survey.question']
        page_1 = Question.create({
            'title': 'Page 1',
            'is_page': True,
            'question_type': False,
            'sequence': 1,
            'random_questions_count': 3
        })
        question_and_pages |= page_1
        question_and_pages = self._add_questions(question_and_pages, page_1, 5)

        page_2 = Question.create({
            'title': 'Page 2',
            'is_page': True,
            'question_type': False,
            'sequence': 100,
            'random_questions_count': 5
        })
        question_and_pages |= page_2
        question_and_pages = self._add_questions(question_and_pages, page_2, 10)

        page_3 = Question.create({
            'title': 'Page 2',
            'is_page': True,
            'question_type': False,
            'sequence': 1000,
            'random_questions_count': 4
        })
        question_and_pages |= page_3
        question_and_pages = self._add_questions(question_and_pages, page_3, 2)

        self.survey1 = self.env['survey.survey'].sudo().create({
            'title': "S0",
            'question_and_page_ids': [(6, 0, question_and_pages.ids)],
            'questions_selection': 'random'
        })

        generated_questions = self.survey1._prepare_user_input_predefined_questions()

        self.assertEqual(len(generated_questions.ids), 10, msg="Expected 10 unique questions")
        self.assertEqual(len(generated_questions.filtered(lambda question: question.page_id == page_1)), 3, msg="Expected 3 questions in page 1")
        self.assertEqual(len(generated_questions.filtered(lambda question: question.page_id == page_2)), 5, msg="Expected 5 questions in page 2")
        self.assertEqual(len(generated_questions.filtered(lambda question: question.page_id == page_3)), 2, msg="Expected 2 questions in page 3")

    def _add_questions(self, question_and_pages, page, count):
        for i in range(count):
            question_and_pages |= self.env['survey.question'].sudo().create({
                'title': page.title + ' Q' + str(i + 1),
                'sequence': page.sequence + (i + 1)
            })

        return question_and_pages
