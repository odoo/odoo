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
        self.env['ir.config_parameter'].sudo().set_param('mail.mail_force_send_limit', None)
        with self.assertSinglePostNotifications([{'partner': self.partner, 'type': 'inbox'}], {
            'message_type': 'user_notification',
            'subtype': 'mail.mt_note',
        }):
            self.event.partner_ids = self.partner

        # remove custom threshold, sends immediately instead of queuing
        email_partner = self.env['res.partner'].create({'name': 'bob invitee', 'email': 'bob.invitee@test.lan'})
        with self.mock_mail_gateway(mail_unlink_sent=False):
            self.event.partner_ids += email_partner
        self.assertMailMail(email_partner, 'sent', author=self.env.ref('base.partner_root'))

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

    def test_message_invite_email_notif_mass_queued(self):
        """Check that more than 20 notified attendees means mails are queued."""
        self.env['ir.config_parameter'].sudo().set_param('mail.mail_force_send_limit', None)
        additional_attendees = self.env['res.partner'].create([{
            'name': f'test{n}',
            'email': f'test{n}@example.com'} for n in range(101)])
        with self.mock_mail_gateway(mail_unlink_sent=False), self.mock_mail_app():
            self.event.partner_ids = additional_attendees

        self.assertNotified(
            self._new_msgs,
            [{
                'is_read': True,
                'partner': partner,
                'type': 'email',
            } for partner in additional_attendees],
        )

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
            self.env['calendar.alarm_manager'].with_context(lastcall=now - relativedelta(minutes=25))._send_reminder()
            self.env.flush_all()
            new_messages = self.env['mail.message'].search([('model', '=', 'calendar.event'), ('res_id', '=', self.event.id), ('subject', '=', 'test event - Reminder')])
            user_message = new_messages.filtered(lambda x: self.event.user_id.partner_id in x.partner_ids)
            self.assertTrue(user_message, "Organizer must receive a reminder")

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

        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            # Create alarm with one hour interval.
            alarm_hour = self.env['calendar.alarm'].create({
                'name': 'Alarm',
                'alarm_type': 'email',
                'interval': 'hours',
                'duration': 1,
            })
            # Create monthly recurrence, ensure the next alarm is set to the first event
            # and then one month later must be set one hour before to the last event.
            with freeze_time('2024-04-16 10:00+0000'):
                now = fields.Datetime.now()
                self.env['calendar.event'].create({
                    'name': "Single Doom's day",
                    'start': now + relativedelta(hours=2),
                    'stop': now + relativedelta(hours=3),
                    'recurrency': True,
                    'rrule_type': 'monthly',
                    'count': 2,
                    'day': 16,
                    'alarm_ids': [fields.Command.link(alarm_hour.id)],
                }).with_context(mail_notrack=True)
                self.env.flush_all()
                # Ensure that there is only one alarm set, exactly for one hour previous the event.
                self.assertEqual(len(capt.records), 1, "Only one trigger must be created for the entire recurrence.")
                self.assertEqual(capt.records.mapped('call_at'), [datetime(2024, 4, 16, 11, 0)], "Alarm must be one hour before the first event.")

            # Garbage-collect the previous trigger from the cron.
            with freeze_time('2024-05-10 11:00+0000'):
                self.env['ir.cron.trigger']._gc_cron_triggers()

            with freeze_time('2024-04-22 10:00+0000'):
                # The next alarm will be set through the next_date selection for the next event.
                # Ensure that there is only one alarm set, exactly for one hour previous the event.
                self.env['calendar.alarm_manager']._send_reminder()
                self.assertEqual(len(capt.records), 1, "Only one trigger must be created for the entire recurrence.")
                self.assertEqual(capt.records.mapped('call_at'), [datetime(2024, 5, 16, 11, 0)], "Alarm must be one hour before the second event.")

    def test_email_alarm_daily_recurrence(self):
        # test email alarm is sent correctly on daily recurrence
        alarm = self.env['calendar.alarm'].create({
            'name': 'Alarm',
            'alarm_type': 'email',
            'interval': 'minutes',
            'duration': 5,
        })
        cron = self.env.ref('calendar.ir_cron_scheduler_alarm')
        cron.lastcall = False
        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-13 10:00+0000'):
                now = fields.Datetime.now()
                self.env['calendar.event'].create({
                    'name': "Recurring Event",
                    'start': now + relativedelta(minutes=15),
                    'stop': now + relativedelta(minutes=20),
                    'recurrency': True,
                    'rrule_type': 'daily',
                    'count': 3,
                    'alarm_ids': [fields.Command.link(alarm.id)],
                }).with_context(mail_notrack=True)
                self.env.flush_all()
                self.assertEqual(len(capt.records), 1, "1 trigger should have been created for the whole recurrence (1)")
                self.assertEqual(capt.records.call_at, datetime(2022, 4, 13, 10, 10))

        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-13 10:11+0000'):
                self.env['calendar.alarm_manager']._send_reminder()
                self.assertEqual(len(capt.records), 1)

        with self.capture_triggers('calendar.ir_cron_scheduler_alarm') as capt:
            with freeze_time('2022-04-14 10:11+0000'):
                self.env['calendar.alarm_manager']._send_reminder()
                self.assertEqual(len(capt.records), 1, "1 trigger should have been created for the whole recurrence (2)")
                self.assertEqual(capt.records.call_at, datetime(2022, 4, 15, 10, 10))

    def test_notification_event_timezone(self):
        """
            Check the domain that decides when calendar events should be notified to the user.
        """
        def search_event():
            return self.env['calendar.event'].search(self.env['res.users']._systray_get_calendar_event_domain())

        self.env.user.tz = 'Europe/Brussels' # UTC +1 15th November 2023
        events = self.env['calendar.event'].create([{
            'name': "Meeting",
            'start': datetime(2023, 11, 15, 18, 0), # 19:00
            'stop': datetime(2023, 11, 15, 19, 0),  # 20:00
        },
        {
            'name': "Tomorrow meeting",
            'start': datetime(2023, 11, 15, 23, 0),  # 00:00 next day
            'stop': datetime(2023, 11, 16, 0, 0),  # 01:00 next day
        }
        ]).with_context(mail_notrack=True)
        with freeze_time('2023-11-15 17:30:00'):    # 18:30 before event
            self.assertEqual(search_event(), events[0])
        with freeze_time('2023-11-15 18:00:00'):    # 19:00 during event
            self.assertEqual(search_event(), events[0])
        with freeze_time('2023-11-15 18:30:00'):    # 19:30 during event
            self.assertEqual(search_event(), events[0])
        with freeze_time('2023-11-15 19:00:00'):    # 20:00 during event
            self.assertEqual(search_event(), events[0])
        with freeze_time('2023-11-15 19:30:00'):    # 20:30 after event
            self.assertEqual(len(search_event()), 0)
        events.unlink()

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

        self.env.user.tz = 'Asia/Manila'  # UTC +8 15th November 2023
        events = self.env['calendar.event'].create([{
            'name': "Very early meeting",
            'start': datetime(2023, 11, 14, 16, 30),  # 0:30
            'stop': datetime(2023, 11, 14, 17, 0),  # 1:00
        },
        {
            'name': "Meeting on 2 days",
            'start': datetime(2023, 11, 15, 15, 30),  # 23:30
            'stop': datetime(2023, 11, 15, 16, 30),  # 0:30 next day
        },
        {
            'name': "Early meeting tomorrow",
            'start': datetime(2023, 11, 15, 23, 0),  # 00:00 next day
            'stop': datetime(2023, 11, 16, 0, 0),  # 01:00 next day
        },
        {
            'name': "All day meeting",
            'allday': True,
            'start': "2023-11-15",
        }
        ]).with_context(mail_notrack=True)
        with freeze_time('2023-11-15 16:00:00'):
            self.assertEqual(len(search_event()), 3)
        events.unlink()
