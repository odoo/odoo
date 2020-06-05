# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.event_crm.tests.common import TestEventCrmCommon


class TestEventFullCommon(TestEventCrmCommon):

    @classmethod
    def setUpClass(cls):
        super(TestEventFullCommon, cls).setUpClass()

        cls.event_product = cls.env['product.product'].create({
            'name': 'Test Registration Product',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'event_ok': True,
            'standard_price': 30.0,
            'type': 'service',
        })

        cls.event_0.write({
            'event_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                    'product_id': cls.event_product.id,
                    'seats_max': 30,
                }), (0, 0, {
                    'name': 'Second Ticket',
                    'product_id': cls.event_product.id,
                })
            ],
        })

        cls.event_question_1 = cls.env['event.question'].create({
            'title': 'Question1',
            'question_type': 'simple_choice',
            'event_id': cls.event_0.id,
            'once_per_order': False,
            'answer_ids': [
                (0, 0, {'name': 'Q1-Answer1'}),
                (0, 0, {'name': 'Q1-Answer2'})
            ],
        })
        cls.event_question_2 = cls.env['event.question'].create({
            'title': 'Question2',
            'question_type': 'simple_choice',
            'event_id': cls.event_0.id,
            'once_per_order': True,
            'answer_ids': [
                (0, 0, {'name': 'Q2-Answer1'}),
                (0, 0, {'name': 'Q2-Answer2'})
            ],
        })
        cls.event_question_3 = cls.env['event.question'].create({
            'title': 'Question3',
            'question_type': 'text_box',
            'event_id': cls.event_0.id,
            'once_per_order': True,
        })

        # make a SO for a customer, selling some tickets
        cls.customer_so = cls.env['sale.order'].with_user(cls.user_sales_salesman).create({
            'partner_id': cls.event_customer.id,
        })

        cls.website_customer_data = [{
            'name': 'My Customer %02d' % x,
            'partner_id': cls.env.ref('base.public_partner').id,
            'email': 'email.%02d@test.example.com' % x,
            'phone': '04560000%02d' % x,
            'registration_answer_ids': [
                (0, 0, {
                    'question_id': cls.event_question_1.id,
                    'value_answer_id': cls.event_question_1.answer_ids[(x % 2)].id,
                }), (0, 0, {
                    'question_id': cls.event_question_2.id,
                    'value_answer_id': cls.event_question_2.answer_ids[(x % 2)].id,
                }), (0, 0, {
                    'question_id': cls.event_question_3.id,
                    'value_text_box': 'CustomerAnswer%s' % x,
                })
            ],
        }  for x in range(0, 4)]

    def assertLeadConvertion(self, rule, registrations, partner=None, **expected):
        super(TestEventFullCommon, self).assertLeadConvertion(rule, registrations, partner=partner, **expected)
        lead = self.env['crm.lead'].sudo().search([
            ('registration_ids', 'in', registrations.ids),
            ('event_lead_rule_id', '=', rule.id)
        ])

        for registration in registrations:
            if not registration.registration_answer_ids:
                continue
            for answer in registration.registration_answer_ids:
                self.assertIn(answer.question_id.title, lead.description)
                if answer.question_type == 'simple_choice':
                    self.assertIn(answer.value_answer_id.name, lead.description)
                else:
                    self.assertIn(answer.value_text_box, lead.description)  # better: check multi line
