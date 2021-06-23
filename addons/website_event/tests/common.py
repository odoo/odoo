# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta, time
from unittest.mock import patch

from odoo.addons.event.tests.common import TestEventCommon
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.fields import Datetime as FieldsDatetime, Date as FieldsDate
from odoo.tests.common import TransactionCase


class EventDtPatcher(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(EventDtPatcher, cls).setUpClass()

        # Mock dates to have reproducible computed fields based on time
        cls.reference_now = datetime(2020, 7, 6, 10, 0, 0)
        cls.reference_today = datetime(2020, 7, 6)

        cls.event_dt = patch(
            'odoo.addons.event.models.event_event.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.wevent_dt = patch(
            'odoo.addons.website_event.models.event_event.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.wevent_main_dt = patch(
            'odoo.addons.website_event.controllers.main.fields.Datetime',
            wraps=FieldsDatetime
        )
        cls.event_date = patch(
            'odoo.addons.event.models.event_event.fields.Date',
            wraps=FieldsDate
        )
        cls.wevent_main_date = patch(
            'odoo.addons.website_event.controllers.main.fields.Date',
            wraps=FieldsDate
        )
        cls.mock_event_dt = cls.event_dt.start()
        cls.mock_wevent_dt = cls.wevent_dt.start()
        cls.mock_wevent_main_dt = cls.wevent_main_dt.start()
        cls.mock_event_date = cls.event_date.start()
        cls.mock_wevent_main_date = cls.wevent_main_date.start()
        cls.mock_event_dt.now.return_value = cls.reference_now
        cls.mock_wevent_dt.now.return_value = cls.reference_now
        cls.mock_wevent_main_dt.now.return_value = cls.reference_now
        cls.mock_event_date.today.return_value = cls.reference_today
        cls.mock_wevent_main_date.today.return_value = cls.reference_today
        cls.addClassCleanup(cls.event_dt.stop)
        cls.addClassCleanup(cls.wevent_dt.stop)
        cls.addClassCleanup(cls.wevent_main_dt.stop)
        cls.addClassCleanup(cls.event_date.stop)
        cls.addClassCleanup(cls.wevent_main_date.stop)


class TestWebsiteEventCommon(TestEventCommon):

    @classmethod
    def setUpClass(cls):
        super(TestWebsiteEventCommon, cls).setUpClass()

        cls.company_main = cls.env.user.company_id
        cls.user_event_web_manager = mail_new_test_user(
            cls.env, login='user_event_web_manager',
            name='Martin Sales Manager', email='crm_manager@test.example.com',
            company_id=cls.company_main.id,
            notification_type='inbox',
            groups='event.group_event_manager,website.group_website_designer',
        )

    def _get_menus(self):
        return set(['Introduction', 'Location', 'Register', 'Community'])

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
                [('name', '=', page_specific + ' ' + event.name)]
            )
            if page_specific in menus_in:
                self.assertTrue(bool(view))
            else:
                self.assertFalse(bool(view))


class TestEventOnlineCommon(TestEventCommon, EventDtPatcher):

    @classmethod
    def setUpClass(cls):
        super(TestEventOnlineCommon, cls).setUpClass()

        # event if 8-18 in Europe/Brussels (DST) (first day: begins at 9, last day: ends at 15)
        cls.event_0.write({
            'date_begin': datetime.combine(cls.reference_now, time(7, 0)) - timedelta(days=1),
            'date_end': datetime.combine(cls.reference_now, time(13, 0)) + timedelta(days=1),
        })

        cls.event_customer.write({
            'website_description': '<p>I am your best customer, %s</p>' % cls.event_customer.name,
        })
        cls.event_customer2.write({
            'website_description': '<p>I am your best customer, %s</p>' % cls.event_customer2.name,
        })
