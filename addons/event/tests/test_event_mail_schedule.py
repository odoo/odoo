# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import contextlib
from datetime import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo import exceptions
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.event.tests.common import EventCase
from odoo.addons.event.models.event_mail import EventMail
from odoo.addons.mail.tests.common import MailCase
from odoo.tests import tagged, users, warmup
from odoo.tools import formataddr, mute_logger


class EventMailCommon(EventCase, MailCase, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # don't be annoyed by enrich cron for query counters (unmodular but hey)
        cls.env['ir.config_parameter'].sudo().set_param('crm.iap.lead.enrich.setting', 'no')

        # give default values for all email aliases and domain
        cls._init_mail_gateway()
        cls._init_mail_servers()

        cls.env.company.write({
            'email': 'info@yourcompany.example.com',
            'name': 'YourCompany',
        })
        cls.event_cron_id = cls.env.ref('event.event_mail_scheduler')

        # deactivate other schedulers to avoid messing with crons
        cls.env['event.mail'].search([]).unlink()
        # consider asynchronous sending as default sending
        cls.env["ir.config_parameter"].set_param("event.event_mail_async", False)

        # freeze some datetimes, and ensure more than 1D+1H before event starts
        # to ease time-based scheduler check
        # Since `now` is used to set the `create_date` of an event and create_date
        # has often microseconds, we set it to ensure that the scheduler we still be
        # launched if scheduled_date == create_date - microseconds
        cls.reference_now = datetime(2021, 3, 20, 14, 30, 15, 123456)
        cls.event_date_begin = datetime(2021, 3, 22, 8, 0, 0)
        cls.event_date_end = datetime(2021, 3, 24, 18, 0, 0)

        cls._setup_test_reports()
        with cls.mock_datetime_and_now(cls, cls.reference_now):
            # create with admin to force create_date
            cls.test_event = cls.env['event.event'].with_user(cls.user_eventmanager).create({
                'name': 'TestEventMail',
                'user_id': cls.user_eventmanager.id,
                'date_begin': cls.event_date_begin,
                'date_end': cls.event_date_end,
                'event_mail_ids': [
                    (0, 0, {  # right at subscription
                        'interval_unit': 'now',
                        'interval_type': 'after_sub',
                        'template_ref': f'mail.template,{cls.template_subscription.id}',
                    }),
                    (0, 0, {  # one hour after subscription
                        'interval_nbr': 1,
                        'interval_unit': 'hours',
                        'interval_type': 'after_sub',
                        'template_ref': f'mail.template,{cls.template_subscription.id}',
                    }),
                    (0, 0, {  # 1 days before event
                        'interval_nbr': 1,
                        'interval_unit': 'days',
                        'interval_type': 'before_event',
                        'template_ref': f'mail.template,{cls.template_reminder.id}',
                    }),
                    (0, 0, {  # immediately after event
                        'interval_nbr': 1,
                        'interval_unit': 'hours',
                        'interval_type': 'after_event',
                        'template_ref': f'mail.template,{cls.template_reminder.id}',
                    }),
                ]
            })

    def setUp(self):
        super().setUp()
        # patch registry to simulate a ready environment
        self.patch(self.env.registry, 'ready', True)
        # we don't use mock_mail_gateway thus want to mock smtp to test the stack
        self._mock_smtplib_connection()

    def execute_event_cron(self, *, freeze_date=None):
        cron = self.event_cron_id.sudo()
        with contextlib.ExitStack() as stack:
            if freeze_date:
                stack.enter_context(self.mock_datetime_and_now(freeze_date))
            stack.enter_context(self.mock_mail_gateway())
            stack.enter_context(self.mock_mail_app())
            stack.enter_context(self.enter_registry_test_mode())
            capture = stack.enter_context(self.capture_triggers('event.event_mail_scheduler'))
            cron.method_direct_trigger()
            return capture


@tagged('event_mail', 'post_install', '-at_install')
class TestMailSchedule(EventMailCommon):

    def test_assert_initial_values(self):
        """ Ensure base values for tests """
        test_event = self.test_event

        # event data
        self.assertEqual(test_event.create_date, self.reference_now)
        self.assertEqual(test_event.date_begin, self.event_date_begin, 'Expressed in current user TZ')
        self.assertEqual(test_event.date_end, self.event_date_end, 'Expressed in current user TZ')
        self.assertEqual(test_event.date_tz, 'Europe/Brussels')
        self.assertEqual(test_event.organizer_id, self.user_eventmanager.company_id.partner_id)
        self.assertEqual(test_event.user_id, self.user_eventmanager)

        # check subscription scheduler
        after_sub_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub'), ('interval_unit', '=', 'now')])
        self.assertEqual(len(after_sub_scheduler), 1, 'event: wrong scheduler creation')
        self.assertFalse(after_sub_scheduler.error_datetime)
        self.assertEqual(after_sub_scheduler.scheduled_date, test_event.create_date.replace(microsecond=0))
        self.assertEqual(after_sub_scheduler.mail_state, 'running')
        self.assertEqual(after_sub_scheduler.mail_count_done, 0)
        after_sub_scheduler_2 = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub'), ('interval_unit', '=', 'hours')])
        self.assertEqual(len(after_sub_scheduler_2), 1, 'event: wrong scheduler creation')
        self.assertFalse(after_sub_scheduler_2.error_datetime)
        self.assertEqual(after_sub_scheduler_2.scheduled_date, test_event.create_date.replace(microsecond=0) + relativedelta(hours=1))
        self.assertEqual(after_sub_scheduler_2.mail_state, 'running')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 0)
        # check before event scheduler
        event_prev_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(event_prev_scheduler), 1, 'event: wrong scheduler creation')
        self.assertFalse(event_prev_scheduler.error_datetime)
        self.assertEqual(event_prev_scheduler.scheduled_date, self.event_date_begin + relativedelta(days=-1))
        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertEqual(event_prev_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_prev_scheduler.mail_count_done, 0)
        # check after event scheduler
        event_next_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_event')])
        self.assertEqual(len(event_next_scheduler), 1, 'event: wrong scheduler creation')
        self.assertFalse(event_next_scheduler.error_datetime)
        self.assertEqual(event_next_scheduler.scheduled_date, self.event_date_end + relativedelta(hours=1))
        self.assertFalse(event_next_scheduler.mail_done)
        self.assertEqual(event_next_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_next_scheduler.mail_count_done, 0)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_eventmanager')
    def test_event_mail_schedule(self):
        """ Test mail scheduling for events """
        test_event = self.test_event.with_env(self.env)
        now = self.reference_now
        schedulers = self.env['event.mail'].search([('event_id', '=', test_event.id)])
        after_sub_scheduler = schedulers.filtered(lambda s: s.interval_type == 'after_sub' and s.interval_unit == 'now')
        after_sub_scheduler_2 = schedulers.filtered(lambda s: s.interval_type == 'after_sub' and s.interval_unit == 'hours')
        event_prev_scheduler = schedulers.filtered(lambda s: s.interval_type == 'before_event')
        event_next_scheduler = schedulers.filtered(lambda s: s.interval_type == 'after_event')

        # check iterative work, update params to check call count
        batch_size, render_limit = 2, 10
        self.env['ir.config_parameter'].sudo().set_param('mail.batch_size', batch_size)
        self.env['ir.config_parameter'].sudo().set_param('mail.render.cron.limit', render_limit)

        # create some registrations
        EventMailRegistration = type(self.env['event.mail.registration'])
        exec_origin = EventMailRegistration._execute_on_registrations
        with patch.object(
                EventMailRegistration, '_execute_on_registrations', autospec=True, wraps=EventMailRegistration, side_effect=exec_origin,
             ) as mock_exec, \
             self.mock_datetime_and_now(now), self.mock_mail_gateway(), \
             self.capture_triggers('event.event_mail_scheduler') as capture:
            attendees = self.env['event.registration'].with_user(self.user_eventuser).create([
                {
                    'event_id': test_event.id,
                    'name': f'Reg{idx}',
                    'email': f'reg1{idx}@example.com',
                } for idx in range(15)] + [{
                    'event_id': test_event.id,
                    'name': 'RegDraft',
                    'email': 'reg_draft@example.com',
                    'state': 'draft',
                }, {
                    'event_id': test_event.id,
                    'name': 'RegCancel',
                    'email': 'reg_cancel@example.com',
                    'state': 'cancel',
                }
            ])

        # iterative check
        self.assertEqual(
            mock_exec.call_count, 5,
            "Should have called 5 times execution (batch of 2 until 10 registrations)"
        )

        # REGISTRATIONS / PRE SCHEDULERS
        # --------------------------------------------------

        # check registration state
        self.assertTrue(all(reg.state == 'open' for reg in attendees[:15]), 'Registrations: should be auto-confirmed')
        self.assertListEqual(attendees[15:].mapped('state'), ['draft', 'cancel'])
        self.assertTrue(all(reg.create_date == now for reg in attendees), 'Registrations: should have open date set to confirm date')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(
            len(after_sub_scheduler.mail_registration_ids), 15,
            'Should have 15 scheduled communication (1 / registration), as we schedule more'
            'than cron limit as create should be quick.')
        for idx, mail_registration in enumerate(after_sub_scheduler.mail_registration_ids):
            self.assertEqual(mail_registration.scheduled_date, now.replace(microsecond=0))
            if idx < 10:
                self.assertTrue(mail_registration.mail_sent, 'event: registration mail should be sent at registration creation')
            else:
                self.assertFalse(mail_registration.mail_sent, 'event: registration mail should be scheduled, too much for limit')
        self.assertEqual(after_sub_scheduler.mail_state, 'running')
        self.assertEqual(after_sub_scheduler.mail_count_done, 10, 'event: not all subscription mails should have been sent as too much for limit')

        # cron should have been triggered for the remaining registrations
        self.assertSchedulerCronTriggers(capture, [now])

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 10, 'event: should have 10 scheduled emails (1 / executed registration)')
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in attendees[:10]],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {test_event.name}',
            })

        # same for second scheduler: scheduled but not sent
        self.assertEqual(
            len(after_sub_scheduler_2.mail_registration_ids), 15,
            'Should have 15 scheduled communication (1 / registration)')
        for mail_registration in after_sub_scheduler_2.mail_registration_ids:
            self.assertEqual(mail_registration.scheduled_date, now.replace(microsecond=0) + relativedelta(hours=1))
            self.assertFalse(mail_registration.mail_sent, 'event: registration mail should be scheduled, not sent')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 0, 'event: all subscription mails should be scheduled, not sent')

        # RE-RUN SCHEDULER TO COMPLETE SENDING
        # --------------------------------------------------

        with patch.object(
               EventMailRegistration, '_execute_on_registrations', autospec=True, wraps=EventMailRegistration, side_effect=exec_origin,
            ) as mock_exec:
            capture = self.execute_event_cron(freeze_date=now)

        # iterative check
        self.assertEqual(
            mock_exec.call_count, 3,
            "Should have called 3 times execution (batch of 2 with 5 registrations left = 3 iterations)"
        )

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(after_sub_scheduler.mail_registration_ids), 15)
        for mail_registration in after_sub_scheduler.mail_registration_ids:
            self.assertEqual(mail_registration.scheduled_date, now.replace(microsecond=0))
            self.assertTrue(mail_registration.mail_sent)
        self.assertEqual(after_sub_scheduler.mail_state, 'running')
        self.assertEqual(
            after_sub_scheduler.mail_count_done, 15,
            'Should have sent all mails, as cron limit is set to 20'
        )

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 5, 'event: should have 5 scheduled emails (1 / executed registration)')
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in attendees[10:15]],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {test_event.name}',
            })

        # SECOND ATTENDEE-BASED SCHEDULER (LATER) - UPDATE ITERATIVE
        # --------------------------------------------------

        # check default behavior, batch of 50 to run up to 1000 attendees
        self.env['ir.config_parameter'].sudo().set_param('mail.batch_size', False)
        self.env['ir.config_parameter'].sudo().set_param('mail.render.cron.limit', False)

        # execute event reminder scheduler explicitly, before scheduled date -> should not do anything
        with self.mock_datetime_and_now(now), self.mock_mail_gateway():
            after_sub_scheduler_2.execute()
        self.assertFalse(any(mail_reg.mail_sent for mail_reg in after_sub_scheduler_2.mail_registration_ids))
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 0)
        self.assertEqual(len(self._new_mails), 0, 'event: should not send mails before scheduled date')

        # execute event reminder scheduler, right at scheduled date -> should sent mails
        now_registration = now + relativedelta(hours=1)
        with patch.object(
                EventMailRegistration, '_execute_on_registrations', autospec=True, wraps=EventMailRegistration, side_effect=exec_origin,
             ) as mock_exec:
            capture = self.execute_event_cron(freeze_date=now_registration)

        # iterative check
        self.assertEqual(
            mock_exec.call_count, 1,
            "Should have called 1 times execution (batch of 50 with 15 registrations = 1 iteration)"
        )

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 15, 'event: should have 15 scheduled communication (1 / registration)')
        self.assertTrue(all(mail_reg.mail_sent for mail_reg in after_sub_scheduler_2.mail_registration_ids))
        self.assertEqual(after_sub_scheduler_2.mail_state, 'running')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 15,
                         'All subscriptions emails should have been sent')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 15, 'event: should have 15 scheduled emails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in attendees[:15]],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {test_event.name}',
            })

        # PRE SCHEDULERS (MOVE FORWARD IN TIME)
        # --------------------------------------------------

        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertEqual(event_prev_scheduler.mail_state, 'scheduled')

        # simulate cron running before scheduled date -> should not do anything
        now_start = self.event_date_begin + relativedelta(hours=-25, microsecond=654321)
        self.execute_event_cron(freeze_date=now_start)

        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertEqual(event_prev_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_prev_scheduler.mail_count_done, 0)
        self.assertEqual(len(self._new_mails), 0)

        # execute cron to run schedulers after scheduled date
        now_start = self.event_date_begin + relativedelta(hours=-23, microsecond=654321)
        self.execute_event_cron(freeze_date=now_start)

        # check that scheduler is finished
        self.assertTrue(event_prev_scheduler.mail_done, 'event: reminder scheduler should have run')
        self.assertEqual(event_prev_scheduler.mail_state, 'sent', 'event: reminder scheduler should have run')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 15, 'event: should have scheduled 15 mails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in attendees[:15]],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Reminder for {test_event.name}: tomorrow',
            })

        # NEW REGISTRATION EFFECT ON SCHEDULERS
        # --------------------------------------------------

        with self.mock_datetime_and_now(now_start), self.mock_mail_gateway():
            new_attendee = self.env['event.registration'].create({
                'event_id': test_event.id,
                'name': 'Reg3',
                'email': 'reg3@example.com',
                'state': 'draft',
            })

        # no more seats
        self.assertEqual(new_attendee.state, 'draft')

        # schedulers state untouched
        self.assertTrue(event_prev_scheduler.mail_done)
        self.assertFalse(event_next_scheduler.mail_done)

        # confirm registration -> should trigger registration schedulers
        # NOTE: currently all schedulers are based on create_date
        # meaning several communications may be sent in the time time
        with self.mock_datetime_and_now(now_start + relativedelta(hours=1)), self.mock_mail_gateway():
            new_attendee.action_confirm()

        # verify that subscription scheduler was auto-executed after new registration confirmed
        self.assertEqual(len(after_sub_scheduler.mail_registration_ids), 16, 'event: should have 16 scheduled communication (1 / registration)')
        new_mail_reg = after_sub_scheduler.mail_registration_ids.filtered(lambda mail_reg: mail_reg.registration_id == new_attendee)
        self.assertEqual(new_mail_reg.scheduled_date, now_start.replace(microsecond=0))
        self.assertTrue(new_mail_reg.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertEqual(after_sub_scheduler.mail_count_done, 16,
                         'event: all subscription mails should have been sent')
        # verify that subscription scheduler was auto-executed after new registration confirmed
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 16, 'event: should have 16 scheduled communication (1 / registration)')
        new_mail_reg = after_sub_scheduler_2.mail_registration_ids.filtered(lambda mail_reg: mail_reg.registration_id == new_attendee)
        self.assertEqual(new_mail_reg.scheduled_date, now_start.replace(microsecond=0) + relativedelta(hours=1))
        self.assertTrue(new_mail_reg.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 16,
                         'event: all subscription mails should have been sent')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 1 scheduled emails (new registration only)')
        # manual check because 2 identical mails are sent and mail tools do not support it easily
        for mail in self._new_mails:
            self.assertEqual(mail.email_from, self.user_eventmanager.company_id.email_formatted)
            self.assertEqual(mail.subject, f'Confirmation for {test_event.name}')
            self.assertEqual(mail.state, 'outgoing')
            self.assertEqual(mail.email_to, formataddr((new_attendee.name, new_attendee.email)))

        # POST SCHEDULERS (MOVE FORWARD IN TIME)
        # --------------------------------------------------

        self.assertFalse(event_next_scheduler.mail_done)

        # execute event reminder scheduler explicitly after its schedule date
        new_end = self.event_date_end + relativedelta(hours=2)
        (attendees + new_attendee).invalidate_recordset(['event_date_range'])
        self.execute_event_cron(freeze_date=new_end)

        # check that scheduler is finished
        self.assertTrue(event_next_scheduler.mail_done, 'event: reminder scheduler should should have run')
        self.assertEqual(event_next_scheduler.mail_state, 'sent', 'event: reminder scheduler should have run')
        self.assertEqual(event_next_scheduler.mail_count_done, 16)

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 16, 'event: should have scheduled 3 mails, one for each registration')
        self.assertMailMailWEmails(
        [formataddr((reg.name, reg.email)) for reg in attendees[:15] + new_attendee],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f"Reminder for {test_event.name}: today",
            })

    @mute_logger('odoo.addons.event.models.event_mail')
    @users('user_eventmanager')
    def test_event_mail_schedule_fail_global_composer(self):
        """ Simulate a fail during composer usage e.g. invalid field path, template
        / model change, ... to check defensive behavior """

        # set template write_uid
        user_admin = self.env.ref('base.user_admin')
        self.template_reminder.with_user(user_admin).write({'name': 'Take Ownership'})

        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")
        self.assertTrue(before_scheduler)
        self._create_registrations(self.test_event, 2)

        error_msg = "Some error"

        def _patched_send_mail(self, *args, **kwargs):
            raise exceptions.ValidationError(error_msg)

        # sending fails
        current_dt = self.reference_now + relativedelta(days=3)
        with patch.object(self.env.registry["mail.compose.message"], "_action_send_mail_mass_mail", _patched_send_mail):
            self.execute_event_cron(freeze_date=current_dt)
        self.assertFalse(before_scheduler.mail_done)
        self.assertMailNotifications(
            self._new_msgs[0],
            [{
                'content': f'Communication for {self.test_event.name}',
                'message_type': 'notification',
                'notif': [
                    {'partner': user_admin.partner_id, 'status': 'sent', 'type': 'inbox'},
                    {'partner': self.user_eventmanager.partner_id, 'status': 'sent', 'type': 'inbox'},
                    {'partner': self.user_eventmanager.company_id.partner_id, 'status': 'ready', 'type': 'email'},
                ],
                'subtype': 'mail.mt_note',
                'mail_mail_values': {
                    'body': f'<p>Communication for {self.test_event.name} scheduled on {before_scheduler.scheduled_date} failed. '
                            f'This may be linked to template <a href="{before_scheduler.get_base_url()}/odoo/mail.template/{self.template_reminder.id}">'
                            f'{self.template_reminder.name} ({self.template_reminder.id})</a>.<br><br>It failed with error Some error.</p>',
                },
            }]
        )
        self.assertEqual(before_scheduler.error_datetime, current_dt.replace(microsecond=0))

        # resend within the same hour -> no more log
        new_dt = self.reference_now + relativedelta(days=3, minutes=59)
        with patch.object(self.env.registry["mail.compose.message"], "_action_send_mail_mass_mail", _patched_send_mail):
            self.execute_event_cron(freeze_date=new_dt)
        self.assertFalse(before_scheduler.mail_done)
        self.assertFalse(self._new_msgs)
        self.assertEqual(before_scheduler.error_datetime, current_dt.replace(microsecond=0))

        # resend in more than one hour -> log again
        new_dt = self.reference_now + relativedelta(days=3, minutes=61)
        with patch.object(self.env.registry["mail.compose.message"], "_action_send_mail_mass_mail", _patched_send_mail):
            self.execute_event_cron(freeze_date=new_dt)
        self.assertFalse(before_scheduler.mail_done)
        self.assertTrue(self._new_msgs)
        self.assertEqual(before_scheduler.error_datetime, new_dt.replace(microsecond=0))

        # send succeeds -> reset error
        self.execute_event_cron(freeze_date=new_dt)
        self.assertTrue(before_scheduler.mail_done)
        self.assertFalse(before_scheduler.error_datetime)

    @mute_logger('odoo.addons.event.models.event_mail', 'odoo.addons.mail.models.mail_render_mixin')
    @users('user_eventmanager')
    def test_event_mail_schedule_fail_global_composer_message(self):
        """ Test message logged depending on issue when trying to send communications """
        # set template write_uid
        user_admin = self.env.ref('base.user_admin')
        # templates are now protected, but bypass the check to force having a bad
        # value in DB
        with patch.object(type(self.template_reminder), '_check_can_be_rendered', return_value=True):
            self.template_reminder.with_user(user_admin).write({
                'name': 'Take Ownership',
                'body_html': '<p>Failing <t t-out="object.evnetypo_id"/></p>',
            })

        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")
        self.assertTrue(before_scheduler)
        self._create_registrations(self.test_event, 2)

        # sending fails
        current_dt = self.reference_now + relativedelta(days=3)
        self.execute_event_cron(freeze_date=current_dt)
        self.assertFalse(before_scheduler.mail_done)
        self.assertMailNotifications(
            self._new_msgs[0],
            [{
                'content': f'Communication for {self.test_event.name}',
                'message_type': 'notification',
                'notif': [
                    {'partner': user_admin.partner_id, 'status': 'sent', 'type': 'inbox'},
                    {'partner': self.user_eventmanager.partner_id, 'status': 'sent', 'type': 'inbox'},
                    {'partner': self.user_eventmanager.company_id.partner_id, 'status': 'ready', 'type': 'email'},
                ],
                'subtype': 'mail.mt_note',
                'mail_mail_values': {
                    'body': f'<p>Communication for {self.test_event.name} scheduled on {before_scheduler.scheduled_date} failed. '
                            f'This is due to an error in template <a href="{before_scheduler.get_base_url()}/odoo/mail.template/{self.template_reminder.id}">'
                            f'{self.template_reminder.name} ({self.template_reminder.id})</a>.'
                            f'<br><br>There is an issue with dynamic placeholder. Actual error received is: '
                            '<br>\'event.registration\' object has no attribute \'evnetypo_id\'.</p>',
                },
            }]
        )
        self.assertEqual(before_scheduler.error_datetime, current_dt.replace(microsecond=0))

    @users('user_eventmanager')
    def test_event_mail_schedule_fail_global_no_registrations(self):
        """ Be sure no registrations = no crash in composer """
        cron = self.env.ref("event.event_mail_scheduler").sudo()
        before_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "before_event")

        self.test_event.registration_ids.unlink()
        self.execute_event_cron(freeze_date=self.reference_now + relativedelta(days=3))
        self.assertTrue(before_scheduler.mail_done)

    @mute_logger(
        'odoo.addons.event.models.event_mail',
        'odoo.addons.event.models.event_mail_registration',
        'odoo.addons.event.models.event_registration',
    )
    def test_event_mail_schedule_fail_registration_composer(self):
        """ Simulate a fail during composer usage e.g. invalid field path, template
        / model change, ... to check defensive behavior """
        onsub_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == "after_sub" and s.interval_unit == "now")
        self.assertTrue(onsub_scheduler)
        self.assertEqual(onsub_scheduler.mail_count_done, 0)

        # set template write_uid
        user_admin = self.env.ref('base.user_admin')
        onsub_scheduler.template_ref.with_user(user_admin).write({'name': 'Take Ownership'})

        def _patched_send_mail(self, *args, **kwargs):
            raise exceptions.ValidationError('Some error')

        test_dt = self.reference_now.replace(microsecond=0) + relativedelta(days=3)
        with patch.object(type(self.env["mail.compose.message"]), "_action_send_mail_mass_mail", _patched_send_mail), \
             self.mock_datetime_and_now(self.reference_now + relativedelta(days=3)), \
             self.mock_mail_gateway(), self.mock_mail_app():
            registration = self.env['event.registration'].with_user(self.user_eventmanager).create({
                "email": "test@email.com",
                "event_id": self.test_event.id,
                "name": "Mitchell Admin",
                "phone": "(255)-595-8393",
            })
        self.assertTrue(registration.exists(), "Registration record should exist after creation.")
        self.assertEqual(onsub_scheduler.mail_count_done, 0)
        self.assertMailNotifications(
            self._new_msgs,
            [{
                'content': f'Communication for {self.test_event.name}',
                'message_type': 'notification',
                'notif': [
                    {'partner': user_admin.partner_id, 'status': 'sent', 'type': 'inbox'},
                    {'partner': self.user_eventmanager.partner_id, 'status': 'sent', 'type': 'inbox'},
                    {'partner': self.user_eventmanager.company_id.partner_id, 'status': 'ready', 'type': 'email'},
                ],
                'subtype': 'mail.mt_note',
                'mail_mail_values': {
                    'body': f'<p>Communication for {self.test_event.name} scheduled on {test_dt} failed. '
                            f'This may be linked to template <a href="{onsub_scheduler.get_base_url()}/odoo/mail.template/{onsub_scheduler.template_ref.id}">'
                            f'{onsub_scheduler.template_ref.name} ({onsub_scheduler.template_ref.id})</a>.<br><br>It failed with error Some error.</p>',
                },
            }]
        )
        self.assertEqual(onsub_scheduler.error_datetime, self.reference_now.replace(microsecond=0) + relativedelta(days=3))

    @mute_logger('odoo.addons.event.models.event_mail')
    @users('user_eventmanager')
    def test_event_mail_schedule_fail_registration_template_removed(self):
        """ Test flow where scheduler fails due to template being removed. """
        after_sub_scheduler = self.test_event.event_mail_ids.filtered(lambda s: s.interval_type == 'after_sub')
        self.assertTrue(after_sub_scheduler)
        self.template_subscription.sudo().unlink()
        self.assertFalse(after_sub_scheduler.exists(), "When removing template, scheduler should be removed")

    @users('user_eventmanager')
    def test_event_mail_schedule_on_slot(self):
        """ Test emails sent globally on slots, notably to test iterative job

        Expected behavior
         - event date_begin: 22 08AM
         - event date_end:   24 18AM
         - schedulers: 1 day before start, immediately after end
         - slots begin:      23 08AM and 24 08AM
         - Nothing happens before (23 - 1) 08AM, as what matters are the slots, not the event
         - Two executions: on 22 08 AM and on 23 08 AM
        """
        test_event = self.test_event.with_env(self.env)

        # check iterative work, update params to check call count
        batch_size, render_limit = 2, 4
        self.env['ir.config_parameter'].sudo().set_param('mail.batch_size', batch_size)
        self.env['ir.config_parameter'].sudo().set_param('mail.render.cron.limit', render_limit)

        # find slot-based schedulers, remove other to avoid noise
        event_prev_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        event_after_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_event')])
        (test_event.event_mail_ids - (event_prev_scheduler + event_after_scheduler)).unlink()

        with self.mock_datetime_and_now(self.reference_now):
            test_event = self.test_event.with_env(self.env)
            test_event.write({
                'is_multi_slots': True,
                # Start and end hours expressed in event tz
                # The slots datetimes will be saved in utc
                'event_slot_ids': [
                    (0, 0, {
                        'date': self.event_date_end.date() - relativedelta(days=1),
                        'end_hour': 18,
                        'start_hour': 8,
                    }),
                    (0, 0, {
                        'date': self.event_date_end.date(),
                        'end_hour': 18,
                        'start_hour': 8,
                    }),
                ],
            })
        # Verify datetimes in UTC
        self.assertEqual(test_event.date_tz, 'Europe/Brussels')
        self.assertEqual(
            test_event.event_slot_ids.mapped('start_datetime'),
            [datetime(2021, 3, 23, 7, 0, 0), datetime(2021, 3, 24, 7, 0, 0)])
        self.assertEqual(
            test_event.event_slot_ids.mapped('end_datetime'),
            [datetime(2021, 3, 23, 17, 0, 0), datetime(2021, 3, 24, 17, 0, 0)])

        # create some registrations
        with self.mock_datetime_and_now(self.reference_now):
            registrations = self.env['event.registration'].with_user(self.user_eventuser).create([
                {
                    'email': f'reg.{idx}.{slot.id}@test.example.com',
                    'event_id': test_event.id,
                    'name': f'Reg-{idx} in {slot.id}',
                    'event_slot_id': slot.id,
                }
                for slot in [test_event.event_slot_ids[0], test_event.event_slot_ids[1]]
                for idx in range(5)
            ])
        self.assertEqual(len(registrations), 10)
        registrations_slot_1 = registrations.filtered(lambda r: r.event_slot_id == test_event.event_slot_ids[0])

        # simulate cron: ok for event-begin, but not for slots -> should not send communication
        current = self.event_date_begin - relativedelta(hours=2)
        self.execute_event_cron(freeze_date=current)
        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertEqual(event_prev_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_prev_scheduler.mail_count_done, 0)
        self.assertEqual(len(self._new_mails), 0)

        # created missing mail.slot
        self.assertEqual(len(event_prev_scheduler.mail_slot_ids), 2)
        self.assertEqual(event_prev_scheduler.mail_slot_ids.event_slot_id, test_event.event_slot_ids)
        for mail_slot in event_prev_scheduler.mail_slot_ids:
            self.assertEqual(mail_slot.mail_count_done, 0)
            self.assertEqual(mail_slot.mail_done, 0)
        mail_slot_1 = event_prev_scheduler.mail_slot_ids.filtered(lambda s: s.event_slot_id.date == self.event_date_end.date() - relativedelta(days=1))
        self.assertEqual(mail_slot_1.scheduled_date, datetime(2021, 3, 22, 7, 0, 0))
        mail_slot_2 = event_prev_scheduler.mail_slot_ids.filtered(lambda s: s.event_slot_id.date == self.event_date_end.date())
        self.assertEqual(mail_slot_2.scheduled_date, datetime(2021, 3, 23, 7, 0, 0))

        # execute cron to run scheduler on first slot
        slot1_before_oneday = datetime(2021, 3, 23, 7, 0, 0) - relativedelta(days=1)
        exec_origin = EventMail._execute_event_based_for_registrations
        with patch.object(
            EventMail, '_execute_event_based_for_registrations', autospec=True, wraps=EventMail, side_effect=exec_origin,
        ) as mock_exec:
            capture = self.execute_event_cron(freeze_date=slot1_before_oneday)
        # produced content
        self.assertEqual(len(self._new_mails), 4, 'Cron limited to size of 2x2')
        self.assertEqual(mock_exec.call_count, 2, '2 calls: 2x2registrations, limit of 4')
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in registrations_slot_1[:4]],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Reminder for {test_event.name}: tomorrow',
            })
        # updated info
        self.assertEqual(mail_slot_1.mail_count_done, 4)
        self.assertFalse(mail_slot_1.mail_done)
        self.assertEqual(event_prev_scheduler.mail_count_done, 4)
        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertSchedulerCronTriggers(capture, [slot1_before_oneday])

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_eventmanager')
    @warmup
    def test_event_mail_schedule_on_subscription(self):
        """ Test emails sent on subscription, notably to avoid bottlenecks """
        test_event = self.test_event.with_env(self.env)
        reference_now = self.reference_now

        # remove on subscription, to create hanging registrations
        schedulers = self.env['event.mail'].search([('event_id', '=', test_event.id)])
        _sub_scheduler = schedulers.filtered(lambda s: s.interval_type == 'after_sub' and s.interval_unit == 'now')
        _sub_scheduler.unlink()

        # consider having hanging registrations, still not processed (e.g. adding
        # a new scheduler after)
        self.env.invalidate_all()
        # event 19 - runbot 21
        # - event_crm: +4 (w demo) / +1 (no demo)
        # nightly: 31 :shrug:
        with self.assertQueryCount(31), self.mock_datetime_and_now(reference_now), \
             self.mock_mail_gateway():
            _existing = self.env['event.registration'].create([
                {
                    'email': f'existing.attendee.{idx}@test.example.com',
                    'event_id': test_event.id,
                    'name': f'Attendee {idx}',
                } for idx in range(5)
            ])
        self.assertEqual(len(self._new_mails), 0)
        self.assertEqual(self.mail_mail_create_mocked.call_count, 0)

        # add on subscription scheduler, then new registrations ! yay ! check what
        # happens with old ones
        test_event.write({'event_mail_ids': [
            (0, 0, {  # right at subscription
                'interval_unit': 'now',
                'interval_type': 'after_sub',
                'template_ref': f'mail.template,{self.template_subscription.id}',
            }),
        ]})
        self.env.invalidate_all()
        # event 49 - runbot 52, +3 with nightly demo (still to check)
        # - event_crm: +2 (no demo)
        # nightly: 64 :shrugs
        with self.assertQueryCount(64), \
             self.mock_datetime_and_now(reference_now + relativedelta(minutes=10)), \
             self.mock_mail_gateway():
            _new = self.env['event.registration'].create([
                {
                    'email': f'new.attendee.{idx}@test.example.com',
                    'event_id': test_event.id,
                    'name': f'New Attendee {idx}',
                } for idx in range(2)
            ])
        self.assertEqual(len(self._new_mails), 2,
                         'EventMail: should be limited to new registrations')
        self.assertEqual(self.mail_mail_create_mocked.call_count, 1,
                         'EventMail: should create mails in batch for new registrations')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_eventmanager')
    def test_event_mail_schedule_on_subscription_async(self):
        """ Async mode for schedulers activated, should not send communication
        in the same transaction. """
        test_event = self.test_event.with_env(self.env)
        cron_event = self.env.ref('event.event_mail_scheduler')
        cron_mail = self.env.ref('mail.ir_cron_mail_scheduler_action')
        reference_now = self.reference_now

        self.env['ir.config_parameter'].sudo().set_param('event.event_mail_async', True)
        with self.capture_triggers(cron_event.id) as capt_event, \
             self.capture_triggers(cron_mail.id) as capt_mail, \
             self.mock_datetime_and_now(reference_now + relativedelta(minutes=10)), \
             self.mock_mail_gateway():
            existing = self.env['event.registration'].create([
                {
                    'email': f'new.async.attendee.{idx}@test.example.com',
                    'event_id': test_event.id,
                    'name': f'New Async Attendee {idx}',
                } for idx in range(5)
            ])
        self.assertEqual(len(self._new_mails), 0)
        self.assertEqual(self.mail_mail_create_mocked.call_count, 0)
        capt_event.records.ensure_one()
        self.assertEqual(capt_event.records.call_at, reference_now.replace(microsecond=0) + relativedelta(minutes=10))
        capt_mail.records.ensure_one()

        # run cron: emails should be send for registrations
        self.execute_event_cron(freeze_date=reference_now + relativedelta(minutes=10))
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in existing],
            "outgoing",
            content=f"Hello your registration to {test_event.name} is confirmed",
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {test_event.name}',
            })


@tagged('event_mail', 'post_install', '-at_install')
class TestMailScheduleInternals(EventMailCommon):

    def test_scheduled_date(self):
        now = self.reference_now.replace(microsecond=0)
        start, end = now + relativedelta(days=1), now + relativedelta(days=5)
        with self.mock_datetime_and_now(self.reference_now):
            event = self.env["event.event"].create({
                "event_mail_ids": False,
                "date_begin": start,
                "date_end": end,
                "name": "Test Scheduled Date",
            })
        self.assertEqual(event.create_date, self.reference_now)
        self.assertFalse(event.event_mail_ids)

        for i_type, i_unit, i_nbr, exp in [
            # attendee: create date
            ("after_sub", "now", 3, now),
            ("after_sub", "hours", 3, now + relativedelta(hours=3)),
            ("after_sub", "days", 3, now + relativedelta(days=3)),
            ("after_sub", "weeks", 3, now + relativedelta(weeks=3)),
            ("after_sub", "months", 3, now + relativedelta(months=3)),
            # event: start date
            ("before_event", "now", 3, start),
            ("before_event", "hours", 3, start - relativedelta(hours=3)),
            ("before_event", "days", 3, start - relativedelta(days=3)),
            ("before_event", "weeks", 3, start - relativedelta(weeks=3)),
            ("before_event", "months", 3, start - relativedelta(months=3)),
            ("after_event_start", "now", 3, start),
            ("after_event_start", "hours", 3, start + relativedelta(hours=3)),
            ("after_event_start", "days", 3, start + relativedelta(days=3)),
            ("after_event_start", "weeks", 3, start + relativedelta(weeks=3)),
            ("after_event_start", "months", 3, start + relativedelta(months=3)),
            # event: end date
            ("after_event", "now", 3, end),
            ("after_event", "hours", 3, end + relativedelta(hours=3)),
            ("after_event", "days", 3, end + relativedelta(days=3)),
            ("after_event", "weeks", 3, end + relativedelta(weeks=3)),
            ("after_event", "days", 3, end + relativedelta(days=3)),
            ("before_event_end", "now", 3, end),
            ("before_event_end", "hours", 3, end - relativedelta(hours=3)),
            ("before_event_end", "days", 3, end - relativedelta(days=3)),
            ("before_event_end", "weeks", 3, end - relativedelta(weeks=3)),
            ("before_event_end", "months", 3, end - relativedelta(months=3)),
        ]:
            with self.subTest(i_type=i_type, i_unit=i_unit, i_nbr=i_nbr):
                event.write({
                    "event_mail_ids": [(5, 0), (0, 0, {
                        "interval_nbr": i_nbr,
                        "interval_type": i_type,
                        "interval_unit": i_unit,
                        "template_ref": f"mail.template,{self.template_subscription.id}",
                    })],
                })
                self.assertEqual(event.event_mail_ids.scheduled_date, exp)

    def test_scheduled_date_execution(self):
        """ Check execution is effectively date-based, and for start-based check
        closed event do not fire their schedulers. """
        now = self.reference_now.replace(microsecond=0)
        start, end = now + relativedelta(days=1), now + relativedelta(days=5)
        with self.mock_datetime_and_now(self.reference_now):
            event = self.env["event.event"].create({
                "event_mail_ids": False,
                "date_begin": start,
                "date_end": end,
                "name": "Test Scheduled Date",
            })
        self.assertEqual(event.create_date, self.reference_now)

        EventMail = type(self.env['event.mail'])
        exec_origin = EventMail._execute_event_based

        for i_type, test_now, should_call in [
            # start date based: launch if in [scheduled, end]
            ('before_event', now + relativedelta(days=1, hours=-3), False),
            ('before_event', now + relativedelta(days=1, hours=-2), True),
            ('before_event', now + relativedelta(days=5), False),
            ('after_event_start', now + relativedelta(days=1, hours=1), False),
            ('after_event_start', now + relativedelta(days=1, hours=2), True),
            ('after_event_start', now + relativedelta(days=5), False),
        ]:
            with self.subTest(i_type=i_type, test_now=test_now):
                event.write({
                    "event_mail_ids": [(5, 0), (0, 0, {
                        "interval_nbr": '2',
                        "interval_type": i_type,
                        "interval_unit": 'hours',
                        "template_ref": f"mail.template,{self.template_subscription.id}",
                    })],
                })
                with patch.object(
                    EventMail, '_execute_event_based', autospec=True, wraps=EventMail, side_effect=exec_origin,
                ) as mock_exec, \
                     self.mock_datetime_and_now(test_now), \
                     self.mock_mail_gateway():
                    event.event_mail_ids.execute()
                self.assertEqual(mock_exec.called, should_call)


    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_unique_event_mail_ids(self):
        # create event with default event_mail_ids lines
        test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
            'name': "TestEvent",
            'date_begin': datetime.now(),
            'date_end': datetime.now() + relativedelta(days=1),
            'seats_max': 2,
            'seats_limited': True,
        })

        event_mail_ids_initial = test_event.event_mail_ids
        self._create_registrations(test_event, 1)

        aftersub = test_event.event_mail_ids.filtered(lambda mail: mail.interval_type == "after_sub")
        self.assertTrue(aftersub)

        self.assertEqual(len(test_event.event_mail_ids), 3, "Should have 3 communication lines")
        self.assertEqual(aftersub.mail_count_done, 1, "Should have sent first mail immediately")

        # change the event type that has event_type_mail_ids having one identical and one non-identical configuration
        event_type = self.env['event.type'].create({
            'name': "Go Sports",
            'event_type_mail_ids': [
                (0, 0, {
                    'interval_nbr': 0,
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription')
                }), (0, 0, {
                    'interval_nbr': 5,
                    'interval_unit': 'hours',
                    'interval_type': 'before_event',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')
                }),
            ]
        })
        test_event.event_type_id = event_type

        self.assertTrue(aftersub in test_event.event_mail_ids, "Sent communication should not have been removed")
        mail_not_done = event_mail_ids_initial - aftersub
        self.assertFalse(test_event.event_mail_ids & mail_not_done, "Other default communication lines should have been removed")

        self.assertEqual(len(test_event.event_mail_ids), 2, "Should now have only two communication lines")
        mails_to_send = test_event.event_mail_ids - aftersub
        duplicate_mails = mails_to_send.filtered(lambda mail:
            mail.notification_type == 'mail' and\
            mail.interval_nbr == 0 and\
            mail.interval_unit == 'now' and\
            mail.interval_type == 'after_sub' and\
            mail.template_ref.id == self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription'))

        self.assertEqual(len(duplicate_mails), 0,
            "The duplicate configuration (first one from event_type.event_type_mail_ids which has same configuration as the sent one) should not have been added")

    def test_scheduler_exclusion_list_usage(self):
        """ Ensure mass mailing blacklist is ignored for registration but applied for event mailing """
        self.env["mail.blacklist"].create({
            "email": self.event_customer.email,
        })
        self.assertTrue(self.event_customer.is_blacklisted)

        self.test_event.registration_ids.unlink()
        start_date = self.reference_now + relativedelta(days=3)
        with self.mock_datetime_and_now(start_date), self.mock_mail_gateway():
            attendee = self.env['event.registration'].create({
                'event_id': self.test_event.id,
                'name': self.event_customer.email,
                'email': self.event_customer.email,
            })

        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(self.event_customer.email, attendee.email)
        self.assertMailMailWEmails(
            [formataddr((attendee.name, attendee.email))],
            'outgoing',
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {self.test_event.name}',
            },
        )

        with self.mock_datetime_and_now(start_date), self.mock_mail_gateway():
            scheduler = self.env['event.mail'].search([('event_id', '=', self.test_event.id)])
            scheduler.execute()

        self.assertEqual(len(self._new_mails), 1)
        self.assertEqual(self.event_customer.email, attendee.email)
        self.assertMailMailWEmails(
            [formataddr((attendee.name, attendee.email))],
            'cancel',
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Reminder for {self.test_event.name}: today',
                'failure_type': 'mail_bl',
            },
        )

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_scheduler_on_archived_cancelled_event(self):
        """ Test mail scheduling for archived or cancelled events """
        # deactivate other schedulers to avoid messing with crons
        self.env['event.mail'].search([]).unlink()

        # freeze some datetimes, and ensure more than 1D+1H before event starts
        # to ease time-based scheduler check
        now = datetime(2023, 7, 24, 14, 30, 15)
        event_date_begin = datetime(2023, 7, 26, 8, 0, 0)
        event_date_end = datetime(2023, 7, 28, 18, 0, 0)

        with self.mock_datetime_and_now(now):
            test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
                'name': 'TestEventMail',
                'date_begin': event_date_begin,
                'date_end': event_date_end,
                'event_mail_ids': [
                    (0, 0, {  # right at subscription
                        'interval_unit': 'now',
                        'interval_type': 'after_sub',
                        'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription')}),
                    (0, 0, {  # 3 hours before event
                        'interval_nbr': 3,
                        'interval_unit': 'hours',
                        'interval_type': 'before_event',
                        'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')})
                ]
            })

        # check event scheduler
        scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id)])
        self.assertEqual(len(scheduler), 2, 'event: wrong scheduler creation')

        event_prev_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])

        with self.mock_datetime_and_now(now), self.mock_mail_gateway():
            self.env['event.registration'].create({
                'event_id': test_event.id,
                'name': 'Reg1',
                'email': 'reg1@example.com',
            })
            self.env['event.registration'].create({
                'event_id': test_event.id,
                'name': 'Reg2',
                'email': 'reg2@example.com',
            })
        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 2 scheduled emails (1 / registration)')

        # Archive the Event
        test_event.action_archive()

        # execute cron to run schedulers
        now_start = event_date_begin + relativedelta(hours=-3)
        self.execute_event_cron(freeze_date=now_start)

        # check that scheduler is not executed
        self.assertFalse(event_prev_scheduler.mail_done, 'event: reminder scheduler should should have run')

        # unarchive to test cancelled event schedulers
        test_event.action_unarchive()

        # event cancelled
        test_event.kanban_state = 'cancel'

        # Mail states should be Cancelled
        for mail_id in test_event.event_mail_ids:
            self.assertEqual(mail_id.mail_state, 'cancelled', 'Mail state should be cancelled')

        self.execute_event_cron(freeze_date=now_start)

        # check that scheduler is not executed for cancelled event
        self.assertEqual(len(self._new_mails), 0, 'No mail should be sent for cancelled event')
        self.assertFalse(event_prev_scheduler.mail_done, 'event: reminder scheduler should should have run')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_scheduler_on_done_event(self):
        """ Test mail scheduling for done events """
        # deactivate other schedulers to avoid messing with crons
        self.env['event.mail'].search([]).unlink()

        # freeze some datetimes, and ensure more than 1D+1H before event starts
        # to ease time-based scheduler check
        now = datetime(2023, 7, 24, 14, 30, 15)
        event_date_begin = datetime(2023, 7, 26, 8, 0, 0)
        event_date_end = datetime(2023, 7, 28, 18, 0, 0)

        with self.mock_datetime_and_now(now):
            test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
                'name': 'TestEventMail',
                'date_begin': event_date_begin,
                'date_end': event_date_end,
                'event_mail_ids': [
                    (0, 0, {  # 3 hours after subscription
                        'interval_nbr': 3,
                        'interval_unit': 'hours',
                        'interval_type': 'after_sub',
                        'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription')}),
                    (0, 0, {  # 3 hours after event end
                        'interval_nbr': 3,
                        'interval_unit': 'hours',
                        'interval_type': 'after_event',
                        'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')}),
                ]
            })

        # check event scheduler
        scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id)])
        self.assertEqual(len(scheduler), 2, 'event: wrong scheduler creation')

        event_after_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_event')])

        with self.mock_datetime_and_now(event_date_begin), self.mock_mail_gateway():
            self.env['event.registration'].create([
                {
                    'event_id': test_event.id,
                    'name': f'Reg.{idx}',
                    'email': f'reg{idx}@example.com',
                } for idx in range(3)
            ])
        # no mails sent directly, should wait a few hours
        self.assertNotSentEmail()

        # for some reasons, event is ended before emails effectively go out
        self.execute_event_cron(freeze_date=event_date_end + relativedelta(hours=1))
        self.assertEqual(len(self._new_mails), 0, 'Registration emails should not be send once event is over, used mainly for tickets / reminders')

        # post-event should be sent even if event ended
        self.execute_event_cron(freeze_date=event_date_end + relativedelta(hours=3))
        self.assertEqual(len(self._new_mails), 3)
        self.assertTrue(event_after_scheduler.mail_done)
