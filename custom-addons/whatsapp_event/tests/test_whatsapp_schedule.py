# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
from datetime import datetime, timedelta
from freezegun import freeze_time
from unittest.mock import patch
from itertools import zip_longest

from odoo import exceptions
from odoo.addons.event.tests.common import EventCase
from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.tests import tagged, users
from odoo.tools import mute_logger


@tagged('event_mail')
class TestWhatsappSchedule(EventCase, WhatsAppCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # test subscription whatsapp template
        cls.whatsapp_template_sub = cls.env['whatsapp.template'].create({
            'body': "{{1}} registration confirmation.",
            'name': "Test subscription",
            'model_id': cls.env['ir.model']._get_id('event.registration'),
            'status': 'approved',
            'phone_field': 'phone',
            'wa_account_id': cls.whatsapp_account.id,
        })
        cls.whatsapp_template_sub.variable_ids.write({
            'field_type': "field",
            'field_name': "event_id",
        })

        # test reminder whatsapp template
        cls.whatsapp_template_rem = cls.env['whatsapp.template'].create({
            'body': "{{1}} reminder.",
            'name': "Test reminder",
            'model_id': cls.env['ir.model']._get_id('event.registration'),
            'status': 'approved',
            'phone_field': 'phone',
            'wa_account_id': cls.whatsapp_account.id,
        })

        cls.whatsapp_template_rem.variable_ids.write({
            'field_type': "field",
            'field_name': "event_id",
        })

        # test event
        cls.reference_now = datetime(2023, 3, 10, 14, 30, 15, 0)
        cls.test_event = cls.env['event.event'].create({
            'date_begin': cls.reference_now + timedelta(days=5),
            'date_end': cls.reference_now + timedelta(days=10),
            'date_tz': 'Europe/Brussels',
            'event_mail_ids': [
                (5, 0),
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'notification_type': 'whatsapp',
                    'template_ref': 'whatsapp.template,%i' % cls.whatsapp_template_sub.id}),
                (0, 0, {  # 3 days before event
                    'interval_nbr': 3,
                    'interval_unit': 'days',
                    'interval_type': 'before_event',
                    'notification_type': 'whatsapp',
                    'template_ref': 'whatsapp.template,%i' % cls.whatsapp_template_rem.id}),
            ],
            'name': 'Test Event',
        })
        with cls.mock_datetime_and_now(cls, cls.reference_now):
            cls.test_attendees = cls.env["event.registration"].create([
                {
                    "event_id": cls.test_event.id,
                    "name": f"WA attendee {idx}",
                    "email": f"_test_reg_{idx}@example.com",
                    "phone": f"+324560000{idx}{idx}",
                } for idx in range(2)
            ])

    @contextmanager
    def mock_datetime_and_now(self, mock_dt):
        """ Used when synchronization date (using env.cr.now()) is important
        in addition to standard datetime mocks. Used mainly to detect sync
        issues. """
        with freeze_time(mock_dt), \
             patch.object(self.env.cr, 'now', lambda: mock_dt):
            yield

    @users('user_eventmanager')
    def test_assert_initial_values(self):
        """ Be sure of our initial setup """
        sub_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "after_sub")
        self.assertEqual(len(sub_scheduler), 1)
        self.assertEqual(sub_scheduler.mail_count_done, 2)
        self.assertTrue(sub_scheduler.mail_done)
        self.assertEqual(sub_scheduler.scheduled_date, self.test_event.create_date.replace(microsecond=0),
                         'event: incorrect scheduled date for checking controller')

        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")
        self.assertEqual(len(before_scheduler), 1)
        self.assertEqual(before_scheduler.mail_count_done, 0)
        self.assertFalse(before_scheduler.mail_done)
        self.assertEqual(before_scheduler.scheduled_date, self.test_event.date_begin + timedelta(days=-3))

    @users('user_eventmanager')
    def test_whatsapp_schedule(self):
        test_event = self.env['event.event'].browse(self.test_event.ids)

        with self.mockWhatsappGateway():
            new_regs = self._create_registrations(test_event, 3)

        # check subscription scheduler
        sub_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub')])

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(sub_scheduler.mail_registration_ids), 5, "2 pre-existing + 3 new")
        self.assertTrue(all(m.mail_sent is True for m in sub_scheduler.mail_registration_ids))
        self.assertEqual(sub_scheduler.mapped('mail_registration_ids.registration_id'), test_event.registration_ids)
        self.assertTrue(sub_scheduler.mail_done)
        self.assertEqual(sub_scheduler.mail_count_done, 5, "2 pre-existing + 3 new")

        # verify that message sent correctly after each registration
        for registration in new_regs:
            self.assertWAMessageFromRecord(registration, status='outgoing')

        # check before event scheduler
        before_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])

        # execute event reminder scheduler explicitly
        with self.mock_datetime_and_now(test_event.date_begin + timedelta(days=-3, hours=1)), \
             self.mockWhatsappGateway():
            before_scheduler.execute()

        self.assertTrue(before_scheduler.mail_done)
        self.assertEqual(before_scheduler.mail_count_done, 5, "2 pre-existing + 3 new")

        test_event.date_begin = self.reference_now + timedelta(hours=1)
        self.assertGreater(self.reference_now, before_scheduler.scheduled_date, 'Scheduler scheduled_date should trigger it.')
        for registration, state in zip_longest(test_event.registration_ids, ['draft', 'open'], fillvalue='cancel'):
            registration.state = state
        before_scheduler.mail_done = False

        with self.mock_datetime_and_now(self.reference_now), self.mockWhatsappGateway():
            before_scheduler.execute()
        self.assertEqual(len(self._new_wa_msg), 2, 'Whatsapp messages were not created')
        self.assertEqual(before_scheduler.filtered(lambda r: r.notification_type == 'whatsapp').mail_count_done, 2,
            'Wrong Whatsapp Sent Count! Probably msg sent to unconfirmed attendees were not included into the Sent Count')

    @mute_logger('odoo.addons.event.models.event_mail')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_global_composer(self):
        # Simulate a fail during composer usage e.g. invalid field path, template
        # model change, ... to check defensive behavior
        cron = self.env.ref("event.event_mail_scheduler").sudo()
        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")

        def _patched_composer_send(self, *args, **kwargs):
            raise exceptions.ValidationError('Some error')

        with patch.object(type(self.env["whatsapp.composer"]), "_send_whatsapp_template", _patched_composer_send):
            with self.mock_datetime_and_now(self.reference_now + timedelta(days=3)), \
                 self.mockWhatsappGateway():
                cron.method_direct_trigger()
        self.assertFalse(before_scheduler.mail_done)

    @mute_logger('odoo.addons.event.models.event_mail',
                 'odoo.addons.whatsapp_event.models.event_mail',
                 'odoo.addons.whatsapp_event.models.event_mail_registration')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_global_no_registrations(self):
        """ Be sure no registrations = no crash in wa composer """
        cron = self.env.ref("event.event_mail_scheduler").sudo()

        self.test_event.registration_ids.unlink()
        with self.mock_datetime_and_now(self.reference_now + timedelta(days=3)), \
             self.mockWhatsappGateway():
            cron.method_direct_trigger()

    @mute_logger('odoo.addons.whatsapp_event.models.event_mail')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_global_template_draft(self):
        """ Test flow where scheduler fails due to template ref being in draft
        when sending global event communication (i.e. only through cron). """
        cron = self.env.ref("event.event_mail_scheduler").sudo()
        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")

        # ensure there is a single draft template (crash in composer)
        self.env["whatsapp.template"].sudo().search(
            [("model_id", "=", self.env["ir.model"]._get_id("event.registration"))]
        ).unlink()
        tpl_draft = self.env['whatsapp.template'].sudo().create({
            "body": "Test reminder",
            "model_id": self.env["ir.model"]._get_id("event.registration"),
            "name": "Draft Fail",
            "phone_field": "phone",
            "status": "draft",
            "wa_account_id": self.whatsapp_account.id,
        })
        before_scheduler.template_ref = tpl_draft

        with self.mock_datetime_and_now(self.reference_now + timedelta(days=3)), \
             self.mockWhatsappGateway():
            cron.method_direct_trigger()
        self.assertFalse(before_scheduler.mail_done)

    @mute_logger('odoo.addons.whatsapp_event.models.event_mail')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_global_template_removed(self):
        """ Test flow where scheduler fails due to template ref being removed
        when sending global event communication (i.e. only through cron). """
        cron = self.env.ref("event.event_mail_scheduler").sudo()
        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")

        # make before event scheduler crash, remove linked template
        self.whatsapp_template_rem.sudo().unlink()

        test_event = self.env['event.event'].browse(self.test_event.ids)

        with self.mockWhatsappGateway():
            _new_regs = self._create_registrations(test_event, 3)

        # execute event reminder scheduler explicitly: should not crash, just skip
        with self.mock_datetime_and_now(self.reference_now + timedelta(days=3)), \
             self.mockWhatsappGateway():
            cron.method_direct_trigger()
        self.assertFalse(before_scheduler.mail_done)

    @mute_logger('odoo.addons.whatsapp_event.models.event_mail_registration')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_registration_composer(self):
        """ Simulate a fail during composer usage e.g. invalid field path, template
        # model change, ... to check defensive behavior """
        onsub_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "after_sub")

        def _patched_composer_send(self, *args, **kwargs):
            raise exceptions.ValidationError('Some error')

        with patch.object(type(self.env["whatsapp.composer"]), "_send_whatsapp_template", _patched_composer_send):
            with self.mockWhatsappGateway():
                registration = self.env['event.registration'].create({
                    "email": "test@email.com",
                    "event_id": self.test_event.id,
                    "name": "Mitchell Admin",
                    "phone": "(255)-595-8393",
                })
        self.assertTrue(registration.exists(), "Registration record should exist after creation.")
        self.assertEqual(onsub_scheduler.mail_count_done, 2)
        self.assertFalse(onsub_scheduler.mail_done)

    @mute_logger('odoo.addons.whatsapp_event.models.event_mail')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_registration_template_draft(self):
        """ Test flow where scheduler fails due to template being draft. """
        # ensure there is a single draft template (crash in composer)
        self.env["whatsapp.template"].sudo().search(
            [("model_id", "=", self.env["ir.model"]._get_id("event.registration"))]
        ).unlink()
        tpl_draft = self.env['whatsapp.template'].sudo().create({
            "body": "Test reminder",
            "model_id": self.env["ir.model"]._get_id("event.registration"),
            "name": "Draft Fail",
            "phone_field": "phone",
            "status": "draft",
            "wa_account_id": self.whatsapp_account.id,
        })
        self.test_event.write({
            'event_mail_ids': [
                (5, 0),
                (0, 0, {  # right at subscription
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'notification_type': 'whatsapp',
                    'template_ref': 'whatsapp.template,%i' % tpl_draft.id}),
            ]
        })
        with self.mockWhatsappGateway():
            registration = self.env['event.registration'].create({
                "email": "test@email.com",
                "event_id": self.test_event.id,
                "name": "Mitchell Admin",
                "phone": "(255)-595-8393",
            })
        self.assertTrue(registration.exists(), "Registration record should exist after creation.")
        sub_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "after_sub")
        self.assertFalse(sub_scheduler.mail_done)

    @mute_logger('odoo.addons.whatsapp_event.models.event_mail')
    @users('user_eventmanager')
    def test_whatsapp_schedule_fail_registration_template_removed(self):
        """ Test flow where scheduler fails due to template being removed. """
        # make on subscription scheduler crash, remove linked template
        self.whatsapp_template_sub.sudo().unlink()
        with self.mockWhatsappGateway():
            registration = self.env['event.registration'].create({
                "email": "test@email.com",
                "event_id": self.test_event.id,
                "name": "Mitchell Admin",
                "phone": "(255)-595-8393",
            })
        self.assertTrue(registration.exists(), "Registration record should exist after creation.")
        sub_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "after_sub")
        self.assertFalse(sub_scheduler.mail_done)
