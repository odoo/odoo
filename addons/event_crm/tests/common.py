# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from dateutil.relativedelta import relativedelta
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common

class TestEventCrmCommon(common.SavepointCase):

    @classmethod
    def setUpClass(cls):
        super(TestEventCrmCommon, cls).setUpClass()

        cls.user_eventmanager = mail_new_test_user(
            cls.env, login='user_eventmanager',
            name='Martine EventManager', email='martine.eventmanager@test.example.com',
            tz='Europe/Brussels', notification_type='inbox',
            company_id=cls.env.ref("base.main_company").id,
            groups='base.group_user,event.group_event_manager',
        )

        cls.test_lead_tag = cls.env['crm.tag'].create({'name': 'TagTest'})

        cls.test_event = cls.env['event.event'].with_user(cls.user_eventmanager).create({
            'name': 'TestEvent',
            'date_begin': datetime.datetime.now() + relativedelta(days=-1),
            'date_end': datetime.datetime.now() + relativedelta(days=1),
        })

        cls.test_rule_attendee = cls.env['event.lead.rule'].with_user(cls.user_eventmanager).create({
            'name': 'TestEventCrm Attendee',
            'lead_creation_basis': 'attendee',
            'event_id': cls.test_event.id,
            'event_registration_filter': [['email', 'ilike', '@example.com']],
            'lead_tag_ids': cls.test_lead_tag,
        })

        cls.test_rule_order = cls.env['event.lead.rule'].with_user(cls.user_eventmanager).create({
            'name': 'TestEventCrm Order',
            'lead_creation_basis': 'order',
            'event_id': cls.test_event.id,
            'event_registration_filter': [['email', 'ilike', '@example.com']],
            'lead_user_id': cls.user_eventmanager.id,
        })

        Registration = cls.env['event.registration']
        test_registration_values = [{
            'event_id': cls.test_event.id,
            'name': 'Main Test Registration',
            'email': 'main@example.com',
            'phone': '0456000042',
        }]
        test_registration_values += [{
            'event_id': cls.test_event.id,
            'name': 'Test Registration %s' % i,
            'email': 'test%s@example.com' % i,
            'phone': '045600009%s' % i,
        } for i in range(2)]
        test_registration_values.append({
            'event_id': cls.test_event.id,
            'name': 'Test Registration Other',
            'email': 'other@other.com',
            'phone': '0456000099',
        })
        Registration.create(test_registration_values)
