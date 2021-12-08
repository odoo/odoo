# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import fields
from odoo.addons.event.tests.common import EventCase
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests.common import SMSCase
from odoo.tests import users


class TestSMSSchedule(EventCase, SMSCase):

    @classmethod
    def setUpClass(cls):
        super(TestSMSSchedule, cls).setUpClass()

        cls.sms_template_sub = cls.env['sms.template'].create({
            'name': 'Test subscription',
            'model_id': cls.env.ref('event.model_event_registration').id,
            'body': '{{ object.event_id.organizer_id.name }} registration confirmation.',
            'lang': '{{ object.partner_id.lang }}'
        })
        cls.sms_template_rem = cls.env['sms.template'].create({
            'name': 'Test reminder',
            'model_id': cls.env.ref('event.model_event_registration').id,
            'body': '{{ object.event_id.organizer_id.name }} reminder',
            'lang': '{{ object.partner_id.lang }}'
        })

        cls.test_event = cls.env['event.event'].create({
            'auto_confirm': True,
            'date_begin': fields.Datetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': fields.Datetime.to_string(datetime.today() + timedelta(days=15)),
            'date_tz': 'Europe/Brussels',
            'event_mail_ids': [
                (5, 0),
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'notification_type': 'sms',
                    'template_ref': 'sms.template,%i' % cls.sms_template_sub.id}),
                (0, 0, {  # 3 days before event
                    'interval_nbr': 3,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'notification_type': 'sms',
                    'template_ref': 'sms.template,%i' % cls.sms_template_rem.id}),
            ],
            'name': 'TestEvent',
        })

    @users('user_eventmanager')
    def test_sms_schedule(self):
        test_event = self.env['event.event'].browse(self.test_event.ids)

        with self.mockSMSGateway():
            self._create_registrations(test_event, 3)

        # check subscription scheduler
        sub_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub')])
        self.assertEqual(len(sub_scheduler), 1)
        self.assertEqual(sub_scheduler.scheduled_date, test_event.create_date, 'event: incorrect scheduled date for checking controller')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(sub_scheduler.mail_registration_ids), 3)
        self.assertTrue(all(m.mail_sent is True for m in sub_scheduler.mail_registration_ids))
        self.assertEqual(sub_scheduler.mapped('mail_registration_ids.registration_id'), test_event.registration_ids)

        sanitized_numbers = []
        for registration in test_event.registration_ids:
            reg_sanitized_number = phone_validation.phone_format(registration.phone, 'BE', '32', force_format='E164')
            sanitized_numbers.append(reg_sanitized_number)
            self.assertSMSOutgoing(
                self.env['res.partner'], reg_sanitized_number,
                content='%s registration confirmation.' % test_event.organizer_id.name)
        self.assertTrue(sub_scheduler.mail_done)
        self.assertEqual(sub_scheduler.mail_count_done, 3)

        # clear notification queue to avoid conflicts when checking next notifications
        self.env['mail.notification'].sudo().search([('sms_number', 'in', sanitized_numbers)]).unlink()
        self.env['sms.sms'].sudo().search([('number', 'in', sanitized_numbers)]).unlink()

        # check before event scheduler
        before_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(before_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(before_scheduler.scheduled_date, test_event.date_begin + timedelta(days=-3))

        # execute event reminder scheduler explicitly
        with self.mockSMSGateway():
            before_scheduler.execute()

        # verify that subscription scheduler was auto-executed after each registration
        for registration in test_event.registration_ids:
            reg_sanitized_number = phone_validation.phone_format(registration.phone, 'BE', '32', force_format='E164')
            self.assertSMSOutgoing(
                self.env['res.partner'], reg_sanitized_number,
                content='%s reminder' % test_event.organizer_id.name)
        self.assertTrue(before_scheduler.mail_done)
        self.assertEqual(before_scheduler.mail_count_done, 3)
