# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo.addons.event.tests.common import TestEventCommon
from odoo.addons.mail.tests.common import MockEmail
from odoo.tools import formataddr, mute_logger


class TestMailSchedule(TestEventCommon, MockEmail):

    @mute_logger('odoo.addons.base.models.ir_model', 'odoo.models')
    def test_event_mail_schedule(self):
        """ Test mail scheduling for events """
        event_cron_id = self.env.ref('event.event_mail_scheduler')

        # deactivate other schedulers to avoid messing with crons
        self.env['event.mail'].search([]).unlink()

        # freeze some datetimes, and ensure more than 1D+1H before event starts
        # to ease time-based scheduler check
        now = datetime(2021, 3, 20, 14, 30, 15)
        event_date_begin = datetime(2021, 3, 22, 8, 0, 0)
        event_date_end = datetime(2021, 3, 24, 18, 0, 0)

        with freeze_time(now):
            test_event = self.env['event.event'].with_user(self.user_eventmanager).create({
                'name': 'TestEventMail',
                'auto_confirm': True,
                'date_begin': event_date_begin,
                'date_end': event_date_end,
                'event_mail_ids': [
                    (0, 0, {  # right at subscription
                        'interval_unit': 'now',
                        'interval_type': 'after_sub',
                        'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_subscription')}),
                    (0, 0, {  # one day after subscription
                        'interval_nbr': 1,
                        'interval_unit': 'hours',
                        'interval_type': 'after_sub',
                        'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_subscription')}),
                    (0, 0, {  # 1 days before event
                        'interval_nbr': 1,
                        'interval_unit': 'days',
                        'interval_type': 'before_event',
                        'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_reminder')}),
                    (0, 0, {  # immediately after event
                        'interval_nbr': 1,
                        'interval_unit': 'hours',
                        'interval_type': 'after_event',
                        'template_id': self.env['ir.model.data'].xmlid_to_res_id('event.event_reminder')}),
                ]
            })

        # check subscription scheduler
        after_sub_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub'), ('interval_unit', '=', 'now')])
        self.assertEqual(len(after_sub_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(after_sub_scheduler.scheduled_date, test_event.create_date)
        self.assertTrue(after_sub_scheduler.done)
        after_sub_scheduler_2 = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_sub'), ('interval_unit', '=', 'hours')])
        self.assertEqual(len(after_sub_scheduler_2), 1, 'event: wrong scheduler creation')
        self.assertEqual(after_sub_scheduler_2.scheduled_date, test_event.create_date + relativedelta(hours=1))
        self.assertTrue(after_sub_scheduler_2.done)
        # check before event scheduler
        event_prev_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'before_event')])
        self.assertEqual(len(event_prev_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(event_prev_scheduler.scheduled_date, event_date_begin + relativedelta(days=-1))
        self.assertFalse(event_prev_scheduler.done)
        # check after event scheduler
        event_next_scheduler = self.env['event.mail'].search([('event_id', '=', test_event.id), ('interval_type', '=', 'after_event')])
        self.assertEqual(len(event_next_scheduler), 1, 'event: wrong scheduler creation')
        self.assertEqual(event_next_scheduler.scheduled_date, event_date_end + relativedelta(hours=1))
        self.assertFalse(event_next_scheduler.done)

        # create some registrations
        with freeze_time(now), self.mock_mail_gateway():
            reg1 = self.env['event.registration'].with_user(self.user_eventuser).create({
                'event_id': test_event.id,
                'name': 'Reg1',
                'email': 'reg1@example.com',
            })
            reg2 = self.env['event.registration'].with_user(self.user_eventuser).create({
                'event_id': test_event.id,
                'name': 'Reg2',
                'email': 'reg2@example.com',
            })

        # REGISTRATIONS / PRE SCHEDULERS
        # --------------------------------------------------

        # check registration state
        self.assertTrue(all(reg.state == 'open' for reg in reg1 + reg2), 'Registrations: should be auto-confirmed')
        self.assertTrue(all(reg.date_open == now for reg in reg1 + reg2), 'Registrations: should have open date set to confirm date')

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(after_sub_scheduler.mail_registration_ids), 2, 'event: should have 2 scheduled communication (1 / registration)')
        for mail_registration in after_sub_scheduler.mail_registration_ids:
            self.assertEqual(mail_registration.scheduled_date, now)
            self.assertTrue(mail_registration.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertTrue(after_sub_scheduler.done, 'event: all subscription mails should have been sent')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 2 scheduled emails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email))],
            'outgoing',
            content=None,
            fields_values={'subject': 'Your registration at %s' % test_event.name,
                           'email_from': self.user_eventmanager.company_id.email_formatted,
                          })

        # same for second scheduler: scheduled but not sent
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 2, 'event: should have 2 scheduled communication (1 / registration)')
        for mail_registration in after_sub_scheduler_2.mail_registration_ids:
            self.assertEqual(mail_registration.scheduled_date, now + relativedelta(hours=1))
            self.assertFalse(mail_registration.mail_sent, 'event: registration mail should be scheduled, not sent')
        self.assertFalse(after_sub_scheduler_2.done, 'event: all subscription mails should be scheduled, not sent')

        # execute event reminder scheduler explicitly, before scheduled date -> should not do anything
        with freeze_time(now), self.mock_mail_gateway():
            after_sub_scheduler_2.execute()
        self.assertFalse(any(mail_reg.mail_sent for mail_reg in after_sub_scheduler_2.mail_registration_ids))
        self.assertFalse(after_sub_scheduler_2.done)
        self.assertEqual(len(self._new_mails), 0, 'event: should not send mails before scheduled date')

        # execute event reminder scheduler explicitly, right at scheduled date -> should sent mails
        now_registration = now + relativedelta(hours=1)
        with freeze_time(now_registration), self.mock_mail_gateway():
            after_sub_scheduler_2.execute()

        # verify that subscription scheduler was auto-executed after each registration
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 2, 'event: should have 2 scheduled communication (1 / registration)')
        self.assertTrue(all(mail_reg.mail_sent for mail_reg in after_sub_scheduler_2.mail_registration_ids))
        # FIXME: field not updated
        # self.assertTrue(after_sub_scheduler_2.done, 'event: all subscription mails should have been sent')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 2 scheduled emails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email))],
            'outgoing',
            content=None,
            fields_values={'subject': 'Your registration at %s' % test_event.name,
                           'email_from': self.user_eventmanager.company_id.email_formatted,
                          })

        # PRE SCHEDULERS (MOVE FORWARD IN TIME)
        # --------------------------------------------------

        self.assertFalse(event_prev_scheduler.mail_sent)
        self.assertFalse(event_prev_scheduler.done)

        # execute event reminder scheduler explicitly, before scheduled date -> should not do anything
        now_start = event_date_begin + relativedelta(hours=-25)
        with freeze_time(now_start), self.mock_mail_gateway():
            event_prev_scheduler.execute()

        self.assertFalse(event_prev_scheduler.mail_sent)
        self.assertFalse(event_prev_scheduler.done)
        self.assertEqual(len(self._new_mails), 0)

        # execute cron to run schedulers
        now_start = event_date_begin + relativedelta(hours=-23)
        with freeze_time(now_start), self.mock_mail_gateway():
            event_cron_id.method_direct_trigger()

        # check that scheduler is finished
        self.assertTrue(event_prev_scheduler.mail_sent, 'event: reminder scheduler should have run')
        self.assertTrue(event_prev_scheduler.done, 'event: reminder scheduler should have run')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have scheduled 2 mails (1 / registration)')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email))],
            'outgoing',
            content=None,
            fields_values={'subject': '%s: tomorrow' % test_event.name,
                           'email_from': self.user_eventmanager.company_id.email_formatted,
                          })

        # NEW REGISTRATION EFFECT ON SCHEDULERS
        # --------------------------------------------------

        test_event.write({'auto_confirm': False})
        with freeze_time(now_start), self.mock_mail_gateway():
            reg3 = self.env['event.registration'].with_user(self.user_eventuser).create({
                'event_id': test_event.id,
                'name': 'Reg3',
                'email': 'reg3@example.com',
            })

        # no more seats
        self.assertEqual(reg3.state, 'draft')

        # schedulers state untouched
        self.assertTrue(event_prev_scheduler.mail_sent)
        self.assertTrue(event_prev_scheduler.mail_sent)
        self.assertFalse(event_next_scheduler.mail_sent)
        self.assertFalse(event_next_scheduler.done)
        self.assertFalse(after_sub_scheduler.done, 'event: scheduler registrations should be lower than effective registrations')
        self.assertFalse(after_sub_scheduler_2.done, 'event: scheduler registrations should be lower than effective registrations')

        # confirm registration -> should trigger registration schedulers
        # NOTE: currently all schedulers are based on date_open which equals create_date
        # meaning several communications may be sent in the time time
        with freeze_time(now_start + relativedelta(hours=1)), self.mock_mail_gateway():
            reg3.action_confirm()

       # verify that subscription scheduler was auto-executed after new registration confirmed
        self.assertEqual(len(after_sub_scheduler.mail_registration_ids), 3, 'event: should have 3 scheduled communication (1 / registration)')
        new_mail_reg = after_sub_scheduler.mail_registration_ids.filtered(lambda mail_reg: mail_reg.registration_id == reg3)
        self.assertEqual(new_mail_reg.scheduled_date, now_start)
        self.assertTrue(new_mail_reg.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertTrue(after_sub_scheduler.done, 'event: all subscription mails should have been sent')

       # verify that subscription scheduler was auto-executed after new registration confirmed
        self.assertEqual(len(after_sub_scheduler_2.mail_registration_ids), 3, 'event: should have 3 scheduled communication (1 / registration)')
        new_mail_reg = after_sub_scheduler_2.mail_registration_ids.filtered(lambda mail_reg: mail_reg.registration_id == reg3)
        self.assertEqual(new_mail_reg.scheduled_date, now_start + relativedelta(hours=1))
        self.assertTrue(new_mail_reg.mail_sent, 'event: registration mail should be sent at registration creation')
        self.assertTrue(after_sub_scheduler_2.done, 'event: all subscription mails should have been sent')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 2, 'event: should have 1 scheduled emails (new registration only)')
        # manual check because 2 identical mails are sent and mail tools do not support it easily
        for mail in self._new_mails:
            self.assertEqual(mail.email_from, self.user_eventmanager.company_id.email_formatted)
            self.assertEqual(mail.subject, 'Your registration at %s' % test_event.name)
            self.assertEqual(mail.state, 'outgoing')
            self.assertEqual(mail.email_to, formataddr((reg3.name, reg3.email)))

        # POST SCHEDULERS (MOVE FORWARD IN TIME)
        # --------------------------------------------------

        self.assertFalse(event_next_scheduler.mail_sent)
        self.assertFalse(event_next_scheduler.done)

        # execute event reminder scheduler explicitly after its schedule date
        new_end = event_date_end + relativedelta(hours=2)
        with freeze_time(new_end), self.mock_mail_gateway():
            event_cron_id.method_direct_trigger()

        # check that scheduler is finished
        self.assertTrue(event_next_scheduler.mail_sent, 'event: reminder scheduler should should have run')
        self.assertTrue(event_next_scheduler.done, 'event: reminder scheduler should have run')

        # check emails effectively sent
        self.assertEqual(len(self._new_mails), 3, 'event: should have scheduled 3 mails, one for each registration')
        self.assertMailMailWEmails(
            [formataddr((reg1.name, reg1.email)), formataddr((reg2.name, reg2.email)), formataddr((reg3.name, reg3.email))],
            'outgoing',
            content=None,
            fields_values={'subject': '%s: today' % test_event.name,
                           'email_from': self.user_eventmanager.company_id.email_formatted,
                          })
