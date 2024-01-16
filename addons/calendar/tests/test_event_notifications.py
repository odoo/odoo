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
            alarm = self.env['calendar.alarm'].create({
                'name': 'Alarm',
                'alarm_type': 'email',
                'interval': 'minutes',
                'duration': 20,
            })
            self.event.write({
                'name': 'test event',
                'start': now + relativedelta(minutes=15),
                'stop': now + relativedelta(minutes=18),
                'partner_ids': [fields.Command.link(self.partner.id)],
                'alarm_ids': [fields.Command.link(alarm.id)],
            })

        capt.records.ensure_one()
        self.assertLessEqual(capt.records.call_at, now)

        with patch.object(fields.Datetime, 'now', lambda: now):
            with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
                'message_type': 'user_notification',
                'subtype': 'mail.mt_note',
            }):
                self.env['calendar.alarm_manager'].with_context(lastcall=now - relativedelta(minutes=15))._send_reminder()

    def test_notification_event_timezone(self):
        """
            Check the domain that decides when calendar events should be notified to the user.
        """
        def search_event():
            return self.env['calendar.event'].search(self.env['res.users']._systray_get_calendar_event_domain())

        self.env.user.tz = 'Europe/Brussels' # UTC +1 15th November 2023
        event = self.env['calendar.event'].create({
            'name': "Meeting",
            'start': datetime(2023, 11, 15, 18, 0), # 19:00
            'stop': datetime(2023, 11, 15, 19, 0),  # 20:00
        }).with_context(mail_notrack=True)
        with freeze_time('2023-11-15 17:30:00'):    # 18:30 before event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-15 18:00:00'):    # 19:00 during event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-15 18:30:00'):    # 19:30 during event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-15 19:00:00'):    # 20:00 during event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-15 19:30:00'):    # 20:30 after event
            self.assertEqual(len(search_event()), 0)
        event.unlink()

        self.env.user.tz = 'America/Lima' # UTC -5 15th November 2023
        event = self.env['calendar.event'].create({
            'name': "Meeting",
            'start': datetime(2023, 11, 16, 0, 0), # 19:00 15th November
            'stop': datetime(2023, 11, 16, 1, 0),  # 20:00 15th November
        }).with_context(mail_notrack=True)
        with freeze_time('2023-11-15 23:30:00'):    # 18:30 before event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-16 00:00:00'):    # 19:00 during event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-16 00:30:00'):    # 19:30 during event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-16 01:00:00'):    # 20:00 during event
            self.assertEqual(search_event(), event)
        with freeze_time('2023-11-16 01:30:00'):    # 20:30 after event
            self.assertEqual(len(search_event()), 0)
        event.unlink()

        event = self.env['calendar.event'].create({
            'name': "Meeting",
            'start': datetime(2023, 11, 16, 21, 0), # 16:00 16th November
            'stop': datetime(2023, 11, 16, 22, 0),  # 27:00 16th November
        }).with_context(mail_notrack=True)
        with freeze_time('2023-11-15 19:00:00'):    # 14:00 the day before event
            self.assertEqual(len(search_event()), 0)
        event.unlink()
