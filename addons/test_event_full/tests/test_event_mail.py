# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from freezegun import freeze_time

from odoo.addons.mail.tests.common import MockEmail
from odoo.addons.sms.tests.common import MockSMS
from odoo.addons.test_event_full.tests.common import TestWEventCommon
from odoo.exceptions import ValidationError
from odoo.tools import mute_logger

class TestTemplateRefModel(TestWEventCommon):

    def test_template_ref_delete_lines(self):
        """ When deleting a template, related lines should be deleted too """
        event_type = self.env['event.type'].create({
            'name': 'Event Type',
            'default_timezone': 'Europe/Brussels',
            'event_type_mail_ids': [
                (0, 0, {
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription')}),
                (0, 0, {
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'notification_type': 'sms',
                    'template_ref': 'sms.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event_sms.sms_template_data_event_registration')}),
            ],
        })

        template_mail = event_type.event_type_mail_ids[0].template_ref
        template_sms = event_type.event_type_mail_ids[1].template_ref

        event = self.env['event.event'].create({
            'name': 'event mail template removed',
            'event_type_id': event_type.id,
            'date_begin': datetime(2020, 2, 1, 8, 30, 0),
            'date_end': datetime(2020, 2, 4, 18, 45, 0),
            'date_tz': 'Europe/Brussels',
        })
        self.assertEqual(len(event_type.event_type_mail_ids), 2)
        self.assertEqual(len(event.event_mail_ids), 2)

        template_mail.unlink()
        self.assertEqual(len(event_type.event_type_mail_ids.exists()), 1)
        self.assertEqual(len(event.event_mail_ids.exists()), 1)

        template_sms.unlink()
        self.assertEqual(len(event_type.event_type_mail_ids.exists()), 0)
        self.assertEqual(len(event.event_mail_ids.exists()), 0)

    def test_template_ref_model_constraint(self):

        test_cases = [
            ('mail', 'mail.template', True),
            ('mail', 'sms.template', False),
            ('sms', 'sms.template', True),
            ('sms', 'mail.template', False),
        ]

        for notification_type, template_type, valid in test_cases:
            with self.subTest(notification_type=notification_type, template_type=template_type):
                if template_type == 'mail.template':
                    template = self.env[template_type].create({
                        'name': 'test template',
                        'model_id': self.env['ir.model']._get_id('event.registration'),
                    })
                else:
                    template = self.env[template_type].create({
                        'name': 'test template',
                        'body': 'Body Test',
                        'model_id': self.env['ir.model']._get_id('event.registration'),
                    })
                if not valid:
                    with self.assertRaises(ValidationError) as cm:
                        self.env['event.mail'].create({
                            'event_id': self.event.id,
                            'notification_type': notification_type,
                            'interval_unit': 'now',
                            'interval_type': 'before_event',
                            'template_ref': template,
                        })
                    if notification_type == 'mail':
                        self.assertEqual(str(cm.exception), 'The template which is referenced should be coming from mail.template model.')
                    else:
                        self.assertEqual(str(cm.exception), 'The template which is referenced should be coming from sms.template model.')

class TestEventSmsMailSchedule(TestWEventCommon, MockEmail, MockSMS):

    @freeze_time('2020-07-06 12:00:00')
    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_mail_before_trigger_sent_count(self):
        """ Emails are sent to both confirmed and unconfirmed attendees.
        This test checks that the count of sent emails includes the emails sent to unconfirmed ones

        Time in the test is frozen to simulate the following state:

                   NOW     Event Start    Event End
                  12:00       13:00        14:00
                    |           |            |
            ──────────────────────────────────────►
            |                   |                time
            ◄─────────────────►
                  3 hours
              Trigger before event
        """
        self.sms_template_rem = self.env['sms.template'].create({
            'name': 'Test reminder',
            'model_id': self.env.ref('event.model_event_registration').id,
            'body': '{{ object.event_id.organizer_id.name }} reminder',
            'lang': '{{ object.partner_id.lang }}'
        })
        test_event = self.env['event.event'].create({
            'name': 'TestEventMail',
            # 'user_id': self.env.ref('base.user_admin').id,
            'auto_confirm': False,
            'date_begin': datetime.now() + timedelta(hours=1),
            'date_end': datetime.now() + timedelta(hours=2),
            'event_mail_ids': [
                (0, 0, {  # email 3 hours before event
                    'interval_nbr': 3,
                    'interval_unit': 'hours',
                    'interval_type': 'before_event',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')}),
                (0, 0, {  # sms 3 hours before event
                    'interval_nbr': 3,
                    'interval_unit': 'hours',
                    'interval_type': 'before_event',
                    'notification_type': 'sms',
                    'template_ref': 'sms.template,%i' % self.sms_template_rem.id}),
            ]
        })
        mail_scheduler = test_event.event_mail_ids
        self.assertEqual(len(mail_scheduler), 2, 'There should be two mail schedulers. One for mail one for sms. Cannot perform test')

        # Add registrations
        self.env['event.registration'].create([{
            'event_id': test_event.id,
            'name': 'RegistrationUnconfirmed',
            'email': 'Registration@Unconfirmed.com',
            'state': 'draft',
        }, {
            'event_id': test_event.id,
            'name': 'RegistrationCanceled',
            'email': 'Registration@Canceled.com',
            'state': 'cancel',
        }, {
            'event_id': test_event.id,
            'name': 'RegistrationConfirmed',
            'email': 'Registration@Confirmed.com',
            'state': 'open',
        }])

        with self.mock_mail_gateway(), self.mockSMSGateway():
            mail_scheduler.execute()

        self.assertEqual(len(self._new_mails), 2, 'Mails were not created')
        self.assertEqual(len(self._new_sms), 2, 'SMS were not created')

        self.assertEqual(test_event.seats_expected, 2, 'Wrong number of expected seats (attendees)')

        self.assertEqual(mail_scheduler.filtered(lambda r: r.notification_type == 'mail').mail_count_done, 2,
            'Wrong Emails Sent Count! Probably emails sent to unconfirmed attendees were not included into the Sent Count')
        self.assertEqual(mail_scheduler.filtered(lambda r: r.notification_type == 'sms').mail_count_done, 2,
            'Wrong SMS Sent Count! Probably SMS sent to unconfirmed attendees were not included into the Sent Count')
