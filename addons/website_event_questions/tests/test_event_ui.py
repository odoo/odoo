# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import fields, tests
from odoo.addons.base.tests.common import HttpCaseWithUserPortal


@tests.tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserPortal):

    def test_01_tickets_questions(self):
        """ Will execute the tour that fills up two tickets with a few questions answers
        and then assert that the answers are correctly saved for each attendee. """

        self.design_fair_event = self.env['event.event'].create({
            'name': 'Design Fair New York',
            'date_begin': fields.Datetime.now() - relativedelta(days=15),
            'date_end': fields.Datetime.now() + relativedelta(days=15),
            'event_ticket_ids': [(0, 0, {
                'name': 'Free',
                'start_sale_datetime': fields.Datetime.now() - relativedelta(days=15)
            }), (0, 0, {
                'name': 'Other',
                'start_sale_datetime': fields.Datetime.now() - relativedelta(days=15)
            })],
            'website_published': True,
            'question_ids': [(0, 0, {
                'title': 'Meal Type',
                'question_type': 'simple_choice',
                'answer_ids': [
                    (0, 0, {'name': 'Mixed'}),
                    (0, 0, {'name': 'Vegetarian'}),
                    (0, 0, {'name': 'Pastafarian'})
                ]
            }), (0, 0, {
                'title': 'Allergies',
                'question_type': 'text_box'
            }), (0, 0, {
                'title': 'How did you learn about this event?',
                'question_type': 'simple_choice',
                'once_per_order': True,
                'answer_ids': [
                    (0, 0, {'name': 'Our website'}),
                    (0, 0, {'name': 'Commercials'}),
                    (0, 0, {'name': 'A friend'})
                ]
            })]
        })

        self.start_tour("/", 'test_tickets_questions', login="portal")

        registrations = self.env['event.registration'].search([
            ('email', 'in', ['attendee-a@gmail.com', 'attendee-b@gmail.com'])
        ])
        self.assertEqual(len(registrations), 2)
        first_registration = registrations.filtered(lambda reg: reg.email == 'attendee-a@gmail.com')
        second_registration = registrations.filtered(lambda reg: reg.email == 'attendee-b@gmail.com')
        self.assertEqual(first_registration.name, 'Attendee A')
        self.assertEqual(first_registration.phone, '+32499123456')
        self.assertEqual(second_registration.name, 'Attendee B')

        event_questions = registrations.mapped('event_id.question_ids')
        self.assertEqual(len(event_questions), 3)

        first_registration_answers = first_registration.registration_answer_ids
        self.assertEqual(len(first_registration_answers), 3)

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'Meal Type'
        ).value_answer_id.name, 'Vegetarian')

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'Allergies'
        ).value_text_box, 'Fish and Nuts')

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'How did you learn about this event?'
        ).value_answer_id.name, 'A friend')

        second_registration_answers = second_registration.registration_answer_ids
        self.assertEqual(len(second_registration_answers), 2)

        self.assertEqual(second_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'Meal Type'
        ).value_answer_id.name, 'Pastafarian')

        self.assertEqual(first_registration_answers.filtered(
            lambda answer: answer.question_id.title == 'How did you learn about this event?'
        ).value_answer_id.name, 'A friend')
