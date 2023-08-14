# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.event_crm.tests.common import TestEventCrmCommon
from odoo.addons.sales_team.tests.common import TestSalesCommon
from odoo.addons.website.tests.test_website_visitor import MockVisitor
from odoo.addons.website_event.tests.common import EventDtPatcher


class TestEventFullCommon(TestEventCrmCommon, TestSalesCommon, EventDtPatcher, MockVisitor):

    @classmethod
    def setUpClass(cls):
        super(TestEventFullCommon, cls).setUpClass()

        # ------------------------------------------------------------
        # TICKET INFORMATIONS
        # ------------------------------------------------------------

        cls.event_product = cls.env['product.product'].create({
            'name': 'Test Registration Product',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'event_ok': True,
            'standard_price': 30.0,
            'type': 'service',
        })

        cls.website = cls.env['website'].search([
            ('company_id', '=', cls.env.user.company_id.id)
        ], limit=1)

        cls.event_0.write({
            # event if 8-18 in Europe/Brussels (DST) (first day: begins at 9, last day: ends at 15)
            'date_begin': datetime.combine(cls.reference_now, time(7, 0)) - timedelta(days=1),
            'date_end': datetime.combine(cls.reference_now, time(13, 0)) + timedelta(days=1),
            # ticket informations
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

        # make a SO for a customer, selling some tickets
        cls.customer_so = cls.env['sale.order'].with_user(cls.user_sales_salesman).create({
            'partner_id': cls.event_customer.id,
        })

        # ------------------------------------------------------------
        # QUESTIONS
        # ------------------------------------------------------------

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

        # ------------------------------------------------------------
        # DATA MARSHMALLING
        # ------------------------------------------------------------

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


class TestWEventCommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal, EventDtPatcher, MockVisitor):

    def setUp(self):
        super(TestWEventCommon, self).setUp()

        self.event_product = self.env['product.product'].create({
            'name': 'Test Event Registration',
            'default_code': 'EVENT_REG',
            'description_sale': 'Mighty Description',
            'list_price': 10,
            'event_ok': True,
            'standard_price': 30.0,
            'type': 'service',
        })

        self.event_tag_category_1 = self.env['event.tag.category'].create({
            'name': 'Type',
            'sequence': 2,
        })
        self.event_tag_category_1_tag_1 = self.env['event.tag'].create({
            'name': 'Online',
            'sequence': 10,
            'category_id': self.event_tag_category_1.id,
            'color': 8,
        })
        self.env['event.event'].search(
            [('name', 'like', '%Online Reveal%')]
        ).write(
            {'name': 'Do not click on me'}
        )
        self.event = self.env['event.event'].create({
            'name': 'Online Reveal TestEvent',
            'auto_confirm': True,
            'stage_id': self.env.ref('event.event_stage_booked').id,
            'address_id': False,
            'user_id': self.user_demo.id,
            'tag_ids': [(4, self.event_tag_category_1_tag_1.id)],
            # event if 8-18 in Europe/Brussels (DST) (first day: begins at 7, last day: ends at 17)
            'date_tz': 'Europe/Brussels',
            'date_begin': datetime.combine(self.reference_now, time(5, 0)) - timedelta(days=1),
            'date_end': datetime.combine(self.reference_now, time(15, 0)) + timedelta(days=1),
            # ticket informations
            'event_ticket_ids': [
                (0, 0, {
                    'name': 'Standard',
                    'product_id': self.event_product.id,
                    'price': 0,
                }), (0, 0, {
                    'name': 'VIP',
                    'product_id': self.event_product.id,
                    'seats_max': 10,
                })
            ],
            # activate menus
            'is_published': True,
            'website_menu': True,
            'website_track': True,
            'website_track_proposal': True,
            'exhibitor_menu': True,
            'community_menu': True,
        })

        self.event_customer = self.env['res.partner'].create({
            'name': 'Constantin Customer',
            'email': 'constantin@test.example.com',
            'country_id': self.env.ref('base.be').id,
            'phone': '0485112233',
            'mobile': False,
        })
        self.event_speaker = self.env['res.partner'].create({
            'name': 'Brandon Freeman',
            'email': 'brandon.freeman55@example.com',
            'phone': '(355)-687-3262',
        })

        # ------------------------------------------------------------
        # QUESTIONS
        # ------------------------------------------------------------

        self.event_question_1 = self.env['event.question'].create({
            'title': 'Which field are you working in',
            'question_type': 'simple_choice',
            'event_id': self.event.id,
            'once_per_order': False,
            'answer_ids': [
                (0, 0, {'name': 'Consumers'}),
                (0, 0, {'name': 'Sales'}),
                (0, 0, {'name': 'Research'}),
            ],
        })
        self.event_question_2 = self.env['event.question'].create({
            'title': 'How did you hear about us ?',
            'question_type': 'text_box',
            'event_id': self.event.id,
            'once_per_order': True,
        })

        # ------------------------------------------------------------
        # TRACKS
        # ------------------------------------------------------------

        self.track_0 = self.env['event.track'].create({
            'name': 'What This Event Is All About',
            'event_id': self.event.id,
            'stage_id': self.env.ref('website_event_track.event_track_stage3').id,
            'date': self.reference_now + timedelta(hours=1),
            'duration': 2,
            'is_published': True,
            'wishlisted_by_default': True,
            'user_id': self.user_admin.id,
            'partner_id': self.event_speaker.id,
        })
        self.track_1 = self.env['event.track'].create({
            'name': 'Live Testimonial',
            'event_id': self.event.id,
            'stage_id': self.env.ref('website_event_track.event_track_stage3').id,
            'date': self.reference_now - timedelta(minutes=30),
            'duration': 0.75,
            'is_published': True,
            'user_id': self.user_admin.id,
            'partner_id': self.event_speaker.id,
        })
        self.track_2 = self.env['event.track'].create({
            'name': 'Our Last Day Together !',
            'event_id': self.event.id,
            'stage_id': self.env.ref('website_event_track.event_track_stage3').id,
            'date': self.reference_now + timedelta(days=1),
            'duration': 0.75,
            'is_published': True,
            'user_id': self.user_admin.id,
            'partner_id': self.event_speaker.id,
        })

        # ------------------------------------------------------------
        # MEETING ROOMS
        # ----------------------------------------------------------

        self.env['event.meeting.room'].create({
            'name': 'Best wood for furniture',
            'summary': 'Let\'s talk about wood types for furniture',
            'target_audience': 'wood expert(s)',
            'is_pinned': True,
            'website_published': True,
            'event_id': self.event.id,
            'room_lang_id': self.env.ref('base.lang_en').id,
            'room_max_capacity': '12',
            'room_participant_count': 9,
        })

        self.event.flush()
