# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import SavepointCase, new_test_user
from odoo.addons.mail.tests.common import MailCase


class TestEventNotifications(SavepointCase, MailCase):

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
            with self.assertBus([(self.env.cr.dbname, 'calendar.alarm', self.partner.id)]):
                self.event.with_context(no_mail_to_attendees=True).write({
                    'start': now + relativedelta(minutes=50),
                    'stop': now + relativedelta(minutes=55),
                    'partner_ids': [(4, self.partner.id)],
                    'alarm_ids': [(4, alarm.id)]
                })
            bus_message = [{
                "alarm_id": alarm.id,
                "event_id": self.event.id,
                "title": "Doom's day",
                "message": self.event.display_time,
                "timer": 20*60,
                "notify_at": fields.Datetime.to_string(now + relativedelta(minutes=20)),
            }]
            notif = self.env['calendar.alarm_manager'].with_user(self.user).get_next_notif()
            self.assertEqual(notif, bus_message)

    def test_email_alarm(self):
        alarm = self.env['calendar.alarm'].create({
            'name': 'Alarm',
            'alarm_type': 'email',
            'interval': 'minutes',
            'duration': 20,
        })
        now = fields.Datetime.now()
        self.event.write({
            'start': now + relativedelta(minutes=15),
            'stop': now + relativedelta(minutes=18),
            'partner_ids': [(4, self.partner.id)],
            'alarm_ids': [(4, alarm.id)],
        })
        with patch.object(fields.Datetime, 'now', lambda: now):
            with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
                'message_type': 'user_notification',
                'subtype': 'mail.mt_note',
            }):
                self.env['calendar.alarm_manager'].with_context(lastcall=now - relativedelta(minutes=15))._get_partner_next_mail(self.partner)
