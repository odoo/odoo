# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class EventCase(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(EventCase, cls).setUpClass()

        cls.admin_user = cls.env.ref('base.user_admin')
        cls.admin_user.write({
            'country_id': cls.env.ref('base.be').id,
            'login': 'admin',
            'notification_type': 'inbox',
        })
        cls.company_admin = cls.admin_user.company_id
        # set country in order to format Belgian numbers
        cls.company_admin.write({
            'country_id': cls.env.ref('base.be').id,
        })

        # Test users to use through the various tests
        cls.user_portal = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='patrick.portal@test.example.com',
            groups='base.group_portal',
            login='portal_test',
            name='Patrick Portal',
            notification_type='email',
            tz='Europe/Brussels',
        )
        cls.user_employee = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='eglantine.employee@test.example.com',
            groups='base.group_user',
            login='user_employee',
            name='Eglantine Employee',
            notification_type='inbox',
            tz='Europe/Brussels',
        )
        cls.user_eventregistrationdesk = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='ursule.eventregistration@test.example.com',
            login='user_eventregistrationdesk',
            groups='base.group_user,event.group_event_registration_desk',
            name='Ursule EventRegistration',
            notification_type='inbox',
            tz='Europe/Brussels',
        )
        cls.user_eventuser = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='ursule.eventuser@test.example.com',
            groups='base.group_user,event.group_event_user',
            login='user_eventuser',
            name='Ursule EventUser',
            notification_type='inbox',
            tz='Europe/Brussels',
        )
        cls.user_eventmanager = mail_new_test_user(
            cls.env,
            company_id=cls.company_admin.id,
            email='martine.eventmanager@test.example.com',
            groups='base.group_user,event.group_event_manager',
            login='user_eventmanager',
            name='Martine EventManager',
            notification_type='inbox',
            tz='Europe/Brussels',
        )

        cls.event_customer = cls.env['res.partner'].create({
            'name': 'Constantin Customer',
            'email': 'constantin@test.example.com',
            'country_id': cls.env.ref('base.be').id,
            'phone': '0485112233',
            'mobile': False,
        })
        cls.event_customer2 = cls.env['res.partner'].create({
            'name': 'Constantin Customer 2',
            'email': 'constantin2@test.example.com',
            'country_id': cls.env.ref('base.be').id,
            'phone': '0456987654',
            'mobile': '0456654321',
        })
        cls.reference_now = fields.Datetime.from_string('2022-09-05 15:11:34')

    @classmethod
    def _create_registrations(cls, event, reg_count):
        # create some registrations
        create_date = fields.Datetime.now()
        registrations = cls.env['event.registration'].create([{
            'create_date': create_date,
            'event_id': event.id,
            'name': f'Test Registration {idx}',
            'email': f'_test_reg_{idx}@example.com',
            'phone': f'04560000{idx}{idx}',
        } for idx in range(0, reg_count)])
        return registrations
