# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time

from odoo.addons.event.tests.common import EventCase
from odoo.addons.mail.tests.common import mail_new_test_user


class OnlineEventCase(EventCase):

    @classmethod
    def setUpClass(cls):
        super(OnlineEventCase, cls).setUpClass()

        cls.company_main = cls.env.user.company_id
        cls.user_event_web_manager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='crm_manager@test.example.com',
            groups='event.group_event_manager,website.group_website_designer',
            login='user_event_web_manager',
            name='Martin Sales Manager',
            notification_type='inbox',
        )

        cls.event_customer.write({
            'website_description': '<p>I am your best customer, %s</p>' % cls.event_customer.name,
        })
        cls.event_customer2.write({
            'website_description': '<p>I am your best customer, %s</p>' % cls.event_customer2.name,
        })

    def _get_menus(self):
        return {'Introduction', 'Community', 'Info', 'Location'}

    def _assert_website_menus(self, event, menus_in=None, menus_out=None):
        self.assertTrue(event.menu_id)

        if menus_in is None:
            menus_in = list(self._get_menus())

        menus = self.env['website.menu'].search([('parent_id', '=', event.menu_id.id)])
        self.assertTrue(len(menus) >= len(menus_in))
        self.assertTrue(all(menu_name in menus.mapped('name') for menu_name in menus_in))
        if menus_out:
            self.assertTrue(all(menu_name not in menus.mapped('name') for menu_name in menus_out))

        for page_specific in ['Introduction', 'Location']:
            view = self.env['ir.ui.view'].search(
                [('name', '=', f'{page_specific} {event.name}')]
            )
            if page_specific in menus_in:
                self.assertTrue(bool(view))
            else:
                self.assertFalse(bool(view))


class TestEventOnlineCommon(OnlineEventCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventOnlineCommon, cls).setUpClass()

        # Mock dates to have reproducible computed fields based on time
        cls.reference_now = datetime(2020, 7, 6, 10, 0, 0)
        cls.reference_today = datetime(2020, 7, 6)

        # event if 8-18 in Europe/Brussels (DST) (first day: begins at 9, last day: ends at 15)
        cls.event_0 = cls.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': datetime.combine(cls.reference_now, time(7, 0)) - timedelta(days=1),
            'date_end': datetime.combine(cls.reference_now, time(13, 0)) + timedelta(days=1),
            'date_tz': 'Europe/Brussels',
        })


class TestEventQuestionCommon(EventCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventQuestionCommon, cls).setUpClass()

        cls.event_type_questions = cls.env['event.type'].create({
            'name': 'Update Type',
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
