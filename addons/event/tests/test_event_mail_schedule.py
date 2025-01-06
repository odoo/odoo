# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.event.tests.common import EventCase
from odoo.addons.mail.tests.common import MockEmail
from odoo.tests import tagged, users, warmup
from odoo.tools import formataddr, mute_logger


@tagged('event_mail', 'post_install', '-at_install')
class TestMailSchedule(EventCase, MockEmail, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

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
            cls.test_event = cls.env['event.event'].create({
                'name': 'TestEventMail',
                'user_id': cls.user_eventmanager.id,
                'date_begin': cls.event_date_begin,
                'date_end': cls.event_date_end,
                'event_mail_ids': [
                    (0, 0, {  # right at subscription
                        'interval_unit': 'now',
                        'interval_type': 'after_sub',
                        'notification_type': 'mail',
                        'template_ref': f'mail.template,{cls.template_subscription.id}',
                    }),
                    (0, 0, {  # one hour after subscription
                        'interval_nbr': 1,
                        'interval_unit': 'hours',
                        'interval_type': 'after_sub',
                        'notification_type': 'mail',
                        'template_ref': f'mail.template,{cls.template_subscription.id}',
                    }),
                    (0, 0, {  # 1 days before event
                        'interval_nbr': 1,
                        'interval_unit': 'days',
                        'interval_type': 'before_event',
                        'notification_type': 'mail',
                        'template_ref': f'mail.template,{cls.template_reminder.id}',
                    }),
                    (0, 0, {  # immediately after event
                        'interval_nbr': 1,
                        'interval_unit': 'hours',
                        'interval_type': 'after_event',
                        'notification_type': 'mail',
                        'template_ref': f'mail.template,{cls.template_reminder.id}',
                    }),
                ]
            })

    def test_assert_initial_values(self):
        """ Ensure base values for tests """
        test_event = self.test_event

        # event data
        self.assertEqual(test_event.create_date, self.reference_now)

        # check subscription scheduler
        after_sub_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub'), ('interval_unit', '=', 'now')])
        self.assertEqual(len(after_sub_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(after_sub_scheduler.scheduled_date, test_event.create_date.replace(microsecond=0))
        self.assertFalse(after_sub_scheduler.mail_done)
        self.assertEqual(after_sub_scheduler.mail_state, 'running')
        self.assertEqual(after_sub_scheduler.mail_count_done, 0)
        after_sub_scheduler_2 = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub'), ('interval_unit', '=', 'hours')])
        self.assertEqual(len(after_sub_scheduler_2), 1, 'event: wrong scheduler creation')
        self.assertEqual(after_sub_scheduler_2.scheduled_date, test_event.create_date.replace(microsecond=0) + relativedelta(hours=1))
        self.assertFalse(after_sub_scheduler_2.mail_done)
        self.assertEqual(after_sub_scheduler_2.mail_state, 'running')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 0)
        # check before event scheduler
        event_prev_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(event_prev_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(event_prev_scheduler.scheduled_date, self.event_date_begin + relativedelta(days=-1))
        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertEqual(event_prev_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_prev_scheduler.mail_count_done, 0)
        # check after event scheduler
        event_next_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_event')])
        self.assertEqual(len(event_next_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(event_next_scheduler.scheduled_date, self.event_date_end + relativedelta(hours=1))
        self.assertFalse(event_next_scheduler.mail_done)
        self.assertEqual(event_next_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_next_scheduler.mail_count_done, 0)

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_eventmanager')
    def test_event_mail_schedule(self):
        """ Test mail scheduling for events """
        # create some registrations
        test_event = self.test_event.with_env(self.env)
        now = self.reference_now
        schedulers = self.env['event.mail'].search([('event_id', '=', test_event.id)])
        after_sub_scheduler = schedulers.filtered(lambda s: s.interval_type == 'after_sub' and s.interval_unit == 'now')
        after_sub_scheduler_2 = schedulers.filtered(lambda s: s.interval_type == 'after_sub' and s.interval_unit == 'hours')
        event_prev_scheduler = schedulers.filtered(lambda s: s.interval_type == 'before_event')
        event_next_scheduler = schedulers.filtered(lambda s: s.interval_type == 'after_event')

        with self.mock_datetime_and_now(now), self.mock_mail_gateway():
            reg1 = self.env['event.registration'].create({
                'event_id': test_event.id,
                'name': 'Reg1',
                'email': 'reg1@example.com',
            })
            reg2 = self.env['event.registration'].create({
                'event_id': test_event.id,
                'name': 'Reg2',
                'email': 'reg2@example.com',
            })
            reg3_draft = self.env['event.registration'].with_user(self.user_eventuser).create({
                'event_id': test_event.id,
                'name': 'Reg3',
                'email': 'reg3_draft@example.com',
            })
            reg4_cancel = self.env['event.registration'].with_user(self.user_eventuser).create({
                'event_id': test_event.id,
                'name': 'Reg4',
                'email': 'reg4_cancel@example.com',
            })

        reg3_draft.action_set_draft()
        reg4_cancel.action_cancel()
        registrations = reg1 + reg2 + reg3_draft + reg4_cancel

        # REGISTRATIONS / PRE SCHEDULERS
        # --------------------------------------------------

        # check registration state
        self.assertListEqual(registrations.mapped('state'), ['open', 'open', 'draft', 'cancel'], 'Registrations: should be auto-confirmed')
        self.assertListEqual(registrations.mapped('create_date'), [now] * 4, 'Registrations: should have open date set to confirm date')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(after_sub_scheduler.mail_registration_ids), 4, 'event: should have 4 scheduled communication (1 / registration)')
        for mail_registration in after_sub_scheduler.mail_registration_ids:
            self.assertEqual(mail_registration.scheduled_date, now.replace(microsecond=0))
            self.assertTrue(mail_registration.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertTrue(after_sub_scheduler.mail_done, 'event: all subscription mails should have been sent')
        self.assertEqual(after_sub_scheduler.mail_state, 'running')
        self.assertEqual(after_sub_scheduler.mail_count_done, 4)

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 4, 'event: should have 4 scheduled emails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email))],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {test_event.name}',
            })

        # same for second scheduler: scheduled but not sent
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 4, 'event: should have 4 scheduled communication (1 / registration)')
        for mail_registration in after_sub_scheduler_2.mail_registration_ids:
            self.assertEqual(mail_registration.scheduled_date, now.replace(microsecond=0) + relativedelta(hours=1))
            self.assertFalse(mail_registration.mail_sent, 'event: registration mail should be scheduled, not sent')
        self.assertFalse(after_sub_scheduler_2.mail_done, 'event: all subscription mails should be scheduled, not sent')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 0)

        # execute event reminder scheduler explicitly, before scheduled date -> should not do anything
        with freeze_time(now), self.mock_mail_gateway():
            after_sub_scheduler_2.execute()
        self.assertFalse(any(mail_reg.mail_sent for mail_reg in after_sub_scheduler_2.mail_registration_ids))
        self.assertFalse(after_sub_scheduler_2.mail_done)
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 0)
        self.assertEqual(len(self._new_mails), 0, 'event: should not send mails before scheduled date')

        # execute event reminder scheduler explicitly, right at scheduled date -> should sent mails
        now_registration = now + relativedelta(hours=1)
        with freeze_time(now_registration), self.mock_mail_gateway():
            after_sub_scheduler_2.execute()

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 4, 'event: should have 4 scheduled communication (1 / open registration)')
        self.assertListEqual(after_sub_scheduler_2.mail_registration_ids.mapped('mail_sent'), [True, True, False, False])
        self.assertTrue(after_sub_scheduler_2.mail_done, 'event: all subscription mails should have been sent')
        self.assertEqual(after_sub_scheduler_2.mail_state, 'running')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 2)

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 2 scheduled emails (1 / open registration)')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email))],
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
        with freeze_time(now_start), self.mock_mail_gateway():
            self.event_cron_id.method_direct_trigger()

        self.assertFalse(event_prev_scheduler.mail_done)
        self.assertEqual(event_prev_scheduler.mail_state, 'scheduled')
        self.assertEqual(event_prev_scheduler.mail_count_done, 0)
        self.assertEqual(len(self._new_mails), 0)

        # execute cron to run schedulers after scheduled date
        now_start = self.event_date_begin + relativedelta(hours=-23, microsecond=654321)
        with freeze_time(now_start), self.mock_mail_gateway():
            self.event_cron_id.method_direct_trigger()

        # check that scheduler is finished
        self.assertTrue(event_prev_scheduler.mail_done, 'event: reminder scheduler should have run')
        self.assertEqual(event_prev_scheduler.mail_state, 'sent', 'event: reminder scheduler should have run')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have scheduled 2 mails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email))],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Reminder for {test_event.name}: tomorrow',
            })

        # NEW REGISTRATION EFFECT ON SCHEDULERS
        # --------------------------------------------------

        with self.mock_datetime_and_now(now_start), self.mock_mail_gateway():
            reg3 = self.env['event.registration'].create({
                'event_id': test_event.id,
                'name': 'Reg3',
                'email': 'reg3@example.com',
                'state': 'draft',
            })

        # no more seats
        self.assertEqual(reg3.state, 'draft')

        # schedulers state untouched
        self.assertTrue(event_prev_scheduler.mail_done)
        self.assertFalse(event_next_scheduler.mail_done)
        self.assertTrue(after_sub_scheduler.mail_done, 'event: scheduler on registration not updated next to draft registration')
        self.assertTrue(after_sub_scheduler_2.mail_done, 'event: scheduler on registration not updated next to draft registration')

        # confirm registration -> should trigger registration schedulers
        # NOTE: currently all schedulers are based on create_date
        # meaning several communications may be sent in the time time
        with self.mock_datetime_and_now(now_start + relativedelta(hours=1)), self.mock_mail_gateway():
            reg3.action_confirm()

        # verify that subscription scheduler was auto-executed after new registration confirmed
        self.assertEqual(len(after_sub_scheduler.mail_registration_ids), 5, 'event: should have 5 scheduled communication (1 / registration)')
        new_mail_reg = after_sub_scheduler.mail_registration_ids.filtered(lambda mail_reg: mail_reg.registration_id == reg3)
        self.assertEqual(new_mail_reg.scheduled_date, now_start.replace(microsecond=0))
        self.assertTrue(new_mail_reg.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertTrue(after_sub_scheduler.mail_done, 'event: all subscription mails should have been sent')
        self.assertEqual(after_sub_scheduler.mail_count_done, 5)
        # verify that subscription scheduler was auto-executed after new registration confirmed
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 5, 'event: should have 5 scheduled communication (1 / registration)')
        new_mail_reg = after_sub_scheduler_2.mail_registration_ids.filtered(lambda mail_reg: mail_reg.registration_id == reg3)
        self.assertEqual(new_mail_reg.scheduled_date, now_start.replace(microsecond=0) + relativedelta(hours=1))
        self.assertTrue(new_mail_reg.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertTrue(after_sub_scheduler_2.mail_done, 'event: all subscription mails should have been sent')
        self.assertEqual(after_sub_scheduler_2.mail_count_done, 3)

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 1 scheduled emails (new registration only)')
        # manual check because 2 identical mails are sent and mail tools do not support it easily
        for mail in self._new_mails:
            self.assertEqual(mail.email_from, self.user_eventmanager.company_id.email_formatted)
            self.assertEqual(mail.subject, f'Confirmation for {test_event.name}')
            self.assertEqual(mail.state, 'outgoing')
            self.assertEqual(mail.email_to, formataddr((reg3.name, reg3.email)))

        # POST SCHEDULERS (MOVE FORWARD IN TIME)
        # --------------------------------------------------

        self.assertFalse(event_next_scheduler.mail_done)

        # execute event reminder scheduler explicitly after its schedule date
        new_end = self.event_date_end + relativedelta(hours=2)
        with self.mock_datetime_and_now(new_end), self.mock_mail_gateway():
            self.event_cron_id.method_direct_trigger()

        # check that scheduler is finished
        self.assertTrue(event_next_scheduler.mail_done, 'event: reminder scheduler should should have run')
        self.assertEqual(event_next_scheduler.mail_state, 'sent', 'event: reminder scheduler should have run')
        self.assertEqual(event_next_scheduler.mail_count_done, 3)

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 3, 'event: should have scheduled 3 mails, one for each registration')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email)), formataddr((reg3.name, reg3.email))],
            'outgoing',
            content=None,
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f"Reminder for {test_event.name}: today",
            })

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
        # event 19
        with self.assertQueryCount(32), self.mock_datetime_and_now(reference_now), \
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
                'notification_type': 'mail',
                'template_ref': f'mail.template,{self.template_subscription.id}',
            }),
        ]})
        self.env.invalidate_all()
        # event 50
        with self.assertQueryCount(63), \
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
        self.assertEqual(self.mail_mail_create_mocked.call_count, 2,
                         'EventMail: should create one mail / new registration')

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    @users('user_eventmanager')
    def test_event_mail_schedule_on_subscription_async(self):
        """ Async mode for schedulers activated, should not send communication
        in the same transaction. """
        test_event = self.test_event.with_env(self.env)
        cron = self.env.ref('event.event_mail_scheduler')
        reference_now = self.reference_now

        self.env['ir.config_parameter'].sudo().set_param('event.event_mail_async', True)
        with self.capture_triggers(cron.id) as capt, \
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
        capt.records.ensure_one()
        self.assertEqual(capt.records.call_at, reference_now.replace(microsecond=0) + relativedelta(minutes=10))

        # run cron: emails should be send for registrations
        with self.mock_datetime_and_now(reference_now + relativedelta(minutes=10)), \
             self.mock_mail_gateway():
            cron.sudo().method_direct_trigger()
        self.assertMailMailWEmails(
            [formataddr((reg.name, reg.email)) for reg in existing],
            "outgoing",
            content=f"Hello your registration to {test_event.name} is confirmed",
            fields_values={
                'email_from': self.user_eventmanager.company_id.email_formatted,
                'subject': f'Confirmation for {test_event.name}',
            })

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

        mail_done = test_event.event_mail_ids.filtered(lambda mail: mail.mail_done and mail.mail_registration_ids)

        self.assertEqual(len(test_event.event_mail_ids), 3, "Should have 3 communication lines")
        self.assertEqual(len(mail_done), 1, "Should have sent first mail immediately")

        # change the event type that has event_type_mail_ids having one identical and one non-identical configuration
        event_type = self.env['event.type'].create({
            'name': "Go Sports",
            'event_type_mail_ids': [
                Command.create({
                    'notification_type': 'mail',
                    'interval_nbr': 0,
                    'interval_unit': 'now',
                    'interval_type': 'after_sub',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription')}),
                Command.create({
                    'notification_type': 'mail',
                    'interval_nbr': 5,
                    'interval_unit': 'hours',
                    'interval_type': 'before_event',
                    'template_ref': 'mail.template,%i' % self.env['ir.model.data']._xmlid_to_res_id('event.event_reminder')}),
            ]
        })
        test_event.event_type_id = event_type

        self.assertTrue(mail_done in test_event.event_mail_ids, "Sent communication should not have been removed")
        mail_not_done = event_mail_ids_initial - mail_done
        self.assertFalse(test_event.event_mail_ids & mail_not_done, "Other default communication lines should have been removed")

        self.assertEqual(len(test_event.event_mail_ids), 2, "Should now have only two communication lines")
        mails_to_send = test_event.event_mail_ids - mail_done
        duplicate_mails = mails_to_send.filtered(lambda mail:
            mail.notification_type == 'mail' and\
            mail.interval_nbr == 0 and\
            mail.interval_unit == 'now' and\
            mail.interval_type == 'after_sub' and\
            mail.template_ref.id == self.env['ir.model.data']._xmlid_to_res_id('event.event_subscription'))

        self.assertEqual(len(duplicate_mails), 0,
            "The duplicate configuration (first one from event_type.event_type_mail_ids which has same configuration as the sent one) should not have been added")

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_archived_event_mail_schedule(self):
        """ Test mail scheduling for archived events """
        event_cron_id = self.env.ref('event.event_mail_scheduler')

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
        with freeze_time(now_start), self.mock_mail_gateway():
            event_cron_id.method_direct_trigger()

        # check that scheduler is not executed
        self.assertFalse(event_prev_scheduler.mail_done, 'event: reminder scheduler should should have run')
