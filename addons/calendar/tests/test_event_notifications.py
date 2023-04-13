# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import fields
from odoo.tests.common import TransactionCase, new_test_user
from odoo.addons.base.tests.test_ir_cron import CronMixinCase
from odoo.addons.mail.tests.common import MailCase


class TestEventNotifications(TransactionCase, MailCase, CronMixinCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['calendar.event'].create({
            'name': "Doom's day",
            'start': datetime(2019, 10, 25, 8, 0),
            'stop': datetime(2019, 10, 27, 18, 0),
        }).with_context(mail_notrack=True)
        cls.user = new_test_user(cls.env, 'xav', email='em@il.com', notification_type='inbox')
        cls.partner = cls.user.partner_id

    def test_message_invite(self):
        with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
            'message_type': 'user_notification',
            'subtype': 'mail.mt_note',
        }):
            self.event.partner_ids = self.partner

    def test_message_invite_allday(self):
        with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
            'message_type': 'user_notification',
            'subtype': 'mail.mt_note',
        }):
            self.env['calendar.event'].with_context(mail_create_nolog=True).create([{
                'name': 'Meeting',
                'allday': True,
                'start_date': fields.Date.today() + relativedelta(days=7),
                'stop_date': fields.Date.today() + relativedelta(days=8),
                'partner_ids': [(4, self.partner.id)],
            }])


    def test_message_invite_self(self):
        with self.assertNoNotifications():
            self.event.with_user(self.user).partner_ids = self.partner

    def test_message_inactive_invite(self):
        self.event.active = False
        with self.assertNoNotifications():
            self.event.partner_ids = self.partner

    def test_message_set_inactive_invite(self):
        self.event.active = False
        with self.assertNoNotifications():
            self.event.write({
                'partner_ids': [(4, self.partner.id)],
                'active': False,
            })

    def test_message_datetime_changed(self):
        self.event.partner_ids = self.partner
        "Invitation to Presentation of the new Calendar"
        with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
            'message_type': 'user_notification',
            'subtype': 'mail.mt_note',
        }):
            self.event.start = fields.Datetime.now() + relativedelta(days=1)

    def test_message_date_changed(self):
        self.event.write({
            'allday': True,
            'start_date': fields.Date.today() + relativedelta(days=7),
            'stop_date': fields.Date.today() + relativedelta(days=8),
        })
        self.event.partner_ids = self.partner
        with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
            'message_type': 'user_notification',
            'subtype': 'mail.mt_note',
        }):
            self.event.start_date += relativedelta(days=-1)

    def test_message_date_changed_past(self):
        self.event.write({
            'allday': True,
            'start_date': fields.Date.today(),
            'stop_date': fields.Date.today() + relativedelta(days=1),
        })
        self.event.partner_ids = self.partner
        with self.assertNoNotifications():
            self.event.write({'start': date(2019, 1, 1)})

    def test_message_set_inactive_date_changed(self):
        self.event.write({
            'allday': True,
            'start_date': date(2019, 10, 15),
            'stop_date': date(2019, 10, 15),
        })
        self.event.partner_ids = self.partner
        with self.assertNoNotifications():
            self.event.write({
                'start_date': self.event.start_date - relativedelta(days=1),
                'active': False,
            })

    def test_message_inactive_date_changed(self):
        self.event.write({
            'allday': True,
            'start_date': date(2019, 10, 15),
            'stop_date': date(2019, 10, 15),
            'active': False,
        })
        self.event.partner_ids = self.partner
        with self.assertNoNotifications():
            self.event.start_date += relativedelta(days=-1)

    def test_message_add_and_date_changed(self):
        self.event.partner_ids -= self.partner
        with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
            'message_type': 'user_notification',
            'subtype': 'mail.mt_note',
        }):
            self.event.write({
                'start': self.event.start - relativedelta(days=1),
                'partner_ids': [(4, self.partner.id)],
            })

    def test_bus_notif(self):
        alarm = self.env['calendar.alarm'].create({
            'name': 'Alarm',
            'alarm_type': 'notification',
            'interval': 'minutes',
            'duration': 30,
        })
        now = fields.Datetime.now()
        with patch.object(fields.Datetime, 'now', lambda: now):
            with self.assertBus([(self.env.cr.dbname, 'res.partner', self.partner.id)], [
                {
                    "type": "calendar.alarm",
                    "payload": [{
                        "alarm_id": alarm.id,
                        "event_id": self.event.id,
                        "title": "Doom's day",
                        "message": self.event.display_time,
                        "timer": 20 * 60,
                        "notify_at": fields.Datetime.to_string(now + relativedelta(minutes=20)),
                    }],
                },
            ]):
                self.event.with_context(no_mail_to_attendees=True).write({
                    'start': now + relativedelta(minutes=50),
                    'stop': now + relativedelta(minutes=55),
                    'partner_ids': [(4, self.partner.id)],
                    'alarm_ids': [(4, alarm.id)]
                })

    def test_email_alarm(self):
        now = fields.Datetime.now()
        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            alarm = self.env['calendar.alarm'].with_user(self.user).create({
                'name': 'Alarm',
                'alarm_type': 'email',
                'interval': 'minutes',
                'duration': 20,
            })
            self.event.with_user(self.user).write({
                'name': 'test event',
                'start': now + relativedelta(minutes=15),
                'stop': now + relativedelta(minutes=18),
                'partner_ids': [fields.Command.link(self.partner.id)],
                'alarm_ids': [fields.Command.link(alarm.id)],
            })
            self.env.flush_all()  # flush is required to make partner_ids be present in the event

        self.assertEqual(len(capt.records), 1)
        self.assertLessEqual(capt.records.call_at, now)

        with patch.object(fields.Datetime, 'now', lambda: now):
            with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
                'message_type': 'user_notification',
                'subtype': 'mail.mt_note',
            }):
                self.env['calendar.alarm_manager'].with_context(lastcall=now - relativedelta(minutes=15))._send_reminder()

    def test_email_alarm_recurrence(self):
        # test that only a single cron trigger is created for recurring events.
        # Once a notification has been sent, the next one should be created.
        # It prevent creating hunderds of cron trigger at event creation
        alarm = self.env['calendar.alarm'].create({
            'name': 'Alarm',
            'alarm_type': 'email',
            'interval': 'minutes',
            'duration': 1,
        })
        cron = self.env.ref('calendar.ir_cron_scheduler_alarm')
        cron.lastcall = False
        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-13 10:00+0000'):
                now = fields.Datetime.now()
                self.env['calendar.event'].create({
                    'name': "Single Doom's day",
                    'start': now + relativedelta(minutes=15),
                    'stop': now + relativedelta(minutes=20),
                    'alarm_ids': [fields.Command.link(alarm.id)],
                }).with_context(mail_notrack=True)
                self.env.flush_all()
                self.assertEqual(len(capt.records), 1)
        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-13 10:00+0000'):
                self.env['calendar.event'].create({
                    'name': "Recurring Doom's day",
                    'start': now + relativedelta(minutes=15),
                    'stop': now + relativedelta(minutes=20),
                    'recurrency': True,
                    'rrule_type': 'monthly',
                    'month_by': 'date',
                    'day': 13,
                    'count': 5,
                    'alarm_ids': [fields.Command.link(alarm.id)],
                }).with_context(mail_notrack=True)
                self.env.flush_all()
                self.assertEqual(len(capt.records), 1, "1 trigger should have been created for the whole recurrence")
                self.assertEqual(capt.records.call_at, datetime(2022, 4, 13, 10, 14))
                self.env['calendar.alarm_manager']._send_reminder()
                self.assertEqual(len(capt.records), 1)

            with freeze_time('2022-04-28 10:00+0000'):
                self.env['ir.cron.trigger']._gc_cron_triggers()

            with freeze_time('2022-05-16 10:00+0000'):
                self.env['calendar.alarm_manager']._send_reminder()
                self.assertEqual(capt.records.mapped('call_at'), [datetime(2022, 6, 13, 10, 14)])
                self.assertEqual(len(capt.records), 1, "1 more trigger should have been created")

        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-13 10:00+0000'):
                now = fields.Datetime.now()
                self.env['calendar.event'].create({
                    'name': "Single Doom's day",
                    'start_date': now.date(),
                    'stop_date': now.date() + relativedelta(days=1),
                    'allday': True,
                    'alarm_ids': [fields.Command.link(alarm.id)],
                }).with_context(mail_notrack=True)
                self.env.flush_all()
                self.assertEqual(len(capt.records), 1)

        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-13 10:00+0000'):
                now = fields.Datetime.now()
                self.env['calendar.event'].create({
                    'name': "Single Doom's day",
                    'start_date': now.date(),
                    'stop_date': now.date() + relativedelta(days=1),
                    'allday': True,
                    'recurrency': True,
                    'rrule_type': 'monthly',
                    'month_by': 'date',
                    'day': 13,
                    'count': 5,
                    'alarm_ids': [fields.Command.link(alarm.id)],
                }).with_context(mail_notrack=True)
                self.env.flush_all()
                self.assertEqual(len(capt.records), 1)
