# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo.addons.event.tests.common import TestEventCommon
from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests.common import SMSCase


class TestSMSSchedule(TestEventCommon, SMSCase):

    @classmethod
    def setUpClass(cls):
        super(TestSMSSchedule, cls).setUpClass()

        cls.sms_template_sub = cls.env['sms.template'].create({
            'name': 'Test subscription',
            'model_id': cls.env.ref('event.model_event_registration').id,
            'body': '${object.event_id.organizer_id.name} registration confirmation.',
            'lang': '${object.partner_id.lang}'
        })
        cls.sms_template_rem = cls.env['sms.template'].create({
            'name': 'Test reminder',
            'model_id': cls.env.ref('event.model_event_registration').id,
            'body': '${object.event_id.organizer_id.name} reminder',
            'lang': '${object.partner_id.lang}'
        })

        cls.event_0.write({
            'event_mail_ids': [
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'notification_type': 'sms',
                    'sms_template_id': cls.sms_template_sub.id}),
                (0, 0, {  # 3 days before event
                    'interval_nbr': 3,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'notification_type': 'sms',
                    'sms_template_id': cls.sms_template_rem.id}),
            ]
        })

    def test_sms_schedule(self):
        with self.mockSMSGateway():
            self._create_registrations(self.event_0, 3)

        # check subscription scheduler
        schedulers = self.env['event.mail'].search([('event_id', '=', self.event_0.id), ('interval_type', '=', 'after_sub')])
        self.assertEqual(len(schedulers), 1)
        self.assertEqual(schedulers.scheduled_date, self.event_0.create_date, 'event: incorrect scheduled date for checking controller')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(schedulers.mail_registration_ids), 3)
        self.assertTrue(all(m.mail_sent is True for m in schedulers.mail_registration_ids))
        self.assertEqual(schedulers.mapped('mail_registration_ids.registration_id'), self.event_0.registration_ids)
        sanitized_numbers = []
        for registration in self.event_0.registration_ids:
            reg_sanitized_number = phone_validation.phone_format(registration.phone, 'BE', '32', force_format='E164')
            sanitized_numbers.append(reg_sanitized_number)
            self.assertSMSOutgoing(
                self.env['res.partner'], reg_sanitized_number,
                content='%s registration confirmation.' % self.event_0.organizer_id.name)

        # clear notification queue to avoid conflicts when checking next notifications
        self.env['mail.notification'].search([('sms_number', 'in', sanitized_numbers)]).unlink()
        self.env['sms.sms'].search([('number', 'in', sanitized_numbers)]).unlink()

        # check before event scheduler
        schedulers = self.env['event.mail'].search([('event_id', '=', self.event_0.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(schedulers), 1, 'event: wrong scheduler creation')
        self.assertEqual(schedulers[0].scheduled_date, self.event_0.date_begin + relativedelta(days=-3))

        # execute event reminder scheduler explicitly
        with self.mockSMSGateway():
            schedulers.execute()

        # verify that subscription scheduler was auto-executed after each registration
        for registration in self.event_0.registration_ids:
            reg_sanitized_number = phone_validation.phone_format(registration.phone, 'BE', '32', force_format='E164')
            self.assertSMSOutgoing(
                self.env['res.partner'], reg_sanitized_number,
                content='%s reminder' % self.event_0.organizer_id.name)
