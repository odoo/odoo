# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timezone
from freezegun import freeze_time
from unittest.mock import patch

from odoo.addons.google_calendar.models.res_users import ResUsers
from odoo.addons.google_calendar.tests.test_sync_common import TestSyncGoogle, patch_api
from odoo.addons.google_calendar.utils.google_event import GoogleEvent
from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import tagged

from .test_token_access import TestTokenAccess


@tagged('odoo2google')
@patch.object(ResUsers, '_get_google_calendar_token', lambda user: user.google_calendar_token)
class TestSyncOdoo2GoogleMail(TestTokenAccess, TestSyncGoogle, MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Make sure this test will work for the next 30 years
        cls.env['ir.config_parameter'].set_int('google_calendar.sync.range_days', 10000)

    @patch_api
    def test_alarm_ids_sync_limit_message(self):
        """ Google Calendar only accepts up to 5 reminders per event.
        Ensure that when a calendar event ends up with more than 5 alarms, a log message is send
        to warn internal users that only the first 5 alarms will be synced.
        """
        def assert_alarm_message(event, count):
            """ Check the alarm limit message is logged on the event a certain number of times. """
            alarm_msgs = self._new_msgs.filtered(lambda m:
                m.model == 'calendar.event' and
                m.res_id == event.id and
                "more than 5 reminders" in m.body
            )
            self.assertEqual(len(alarm_msgs), count)

        user = self.organizer_user
        alarms = self.env['calendar.alarm'].create([{
            'name': 'Notif %s' % i,
            'alarm_type': 'notification',
            'interval': 'minutes',
            'duration': 1 + i,  # Making sure each alarm is different
        } for i in range(6)])
        all_alarms = [(4, alarm.id) for alarm in alarms]
        base_vals = {
            'name': 'Event',
            'user_id': user.id,
            'partner_ids': user.partner_id.ids,
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
        }

        with self.mock_mail_app():
            # Not synced: no message should be send
            self.assertFalse(user.is_google_calendar_synced())
            existing_event_over_limit = self.env['calendar.event'].create({**base_vals, 'alarm_ids': all_alarms})
            assert_alarm_message(existing_event_over_limit, 0)
            # Synced: message should be send when the synchronization is restarted
            self.env['res.users.settings']._find_or_create_for_user(user).write({
                'google_calendar_rtoken': 'my_new_rtoken',
                'google_calendar_token': 'my_new_token',
            })
            user.with_user(user).restart_google_synchronization()
            self.assertTrue(user.is_google_calendar_synced())
            assert_alarm_message(existing_event_over_limit, 1)
            # Create
            event_under_limit = self.env['calendar.event'].create({**base_vals, 'alarm_ids': [(4, alarms[0].id)]})
            assert_alarm_message(event_under_limit, 0)
            event_over_limit = self.env['calendar.event'].create({**base_vals, 'alarm_ids': all_alarms})
            assert_alarm_message(event_over_limit, 1)
            # Write
            event_under_limit.write({'alarm_ids': [(4, alarms[1].id)]})
            assert_alarm_message(event_under_limit, 0)
            event_under_limit.write({'alarm_ids': all_alarms})
            assert_alarm_message(event_under_limit, 1)
            # Same alarms, no new message
            event_over_limit.write({'alarm_ids': all_alarms})
            assert_alarm_message(event_over_limit, 1)
            # Change alarms, still over limit should log again
            extra_alarm = self.env['calendar.alarm'].create({
                'name': 'Notif extra',
                'alarm_type': 'notification',
                'interval': 'minutes',
                'duration': 99,
            })
            event_over_limit.write({'alarm_ids': [(4, extra_alarm.id)]})
            assert_alarm_message(event_over_limit, 2)
            # Google -> Odoo Sync
            # Shouldn't log if the alarms are unchanged (5 max from Google merged into the 7 of Odoo).
            event_over_limit.write({'google_id': 'google_event_over_limit'})
            google_values = {
                'id': event_over_limit.google_id,
                'updated': event_over_limit.write_date.replace(tzinfo=timezone.utc).isoformat(),
                'start': {'dateTime': event_over_limit.start.replace(tzinfo=timezone.utc).isoformat()},
                'end': {'dateTime': event_over_limit.stop.replace(tzinfo=timezone.utc).isoformat()},
                'organizer': {'email': user.email},
                'guestsCanModify': True,
                'reminders': {
                    'useDefault': False,
                    'overrides': [{'method': 'popup', 'minutes': alarm.duration_minutes} for alarm in alarms.sorted('id')[:5]],
                },
            }
            synced_event_over_limit = self.env['calendar.event']._sync_google2odoo(GoogleEvent([google_values]))
            self.assertEqual(synced_event_over_limit, event_over_limit)
            self.assertEqual(len(event_over_limit.alarm_ids), 7)
            assert_alarm_message(event_over_limit, 2)
            # Should log if the Google event alarms has changed (1 new from Google added to the 7 of Odoo).
            google_values.update({
                'updated': event_over_limit.write_date.replace(tzinfo=timezone.utc).isoformat(),
                'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 2000}]},
            })
            self.env['calendar.event']._sync_google2odoo(GoogleEvent([google_values]))
            self.assertEqual(len(event_over_limit.alarm_ids), 8)
            assert_alarm_message(event_over_limit, 3)

    @freeze_time("2020-01-01")
    def test_event_creation_for_user(self):
        organizer1 = self.users[0]
        organizer2 = self.users[1]
        user_root = self.env.ref('base.user_root')
        organizer1.google_calendar_token = 'abc'
        organizer2.google_calendar_token = False
        event_values = {
            'name': "Event",
            'start': datetime(2020, 1, 15, 8, 0),
            'stop': datetime(2020, 1, 15, 18, 0),
        }
        partner = self.env['res.partner'].create({'name': 'Jean-Luc', 'email': 'jean-luc@opoo.com'})
        for create_user, organizer, responsible, expect_mail, is_public in [
            (user_root, organizer1, organizer1, False, True), (user_root, None, user_root, True, True),
                (organizer1, None, organizer1, False, False), (organizer1, organizer2, organizer1, False, True)]:
            with self.subTest(create_uid=create_user.name if create_user else None, user_id=organizer.name if organizer else None):
                with self.mock_mail_gateway(), self.mock_google_sync(user_id=responsible):
                    self.env['calendar.event'].with_user(create_user).create({
                        **event_values,
                        'partner_ids': [(4, partner.id)],
                        'user_id': organizer.id if organizer else False,
                    })
                if not expect_mail:
                    self.assertNotSentEmail()
                    self.assertGoogleEventInserted({
                        'attendees': [{'email': 'jean-luc@opoo.com', 'responseStatus': 'needsAction'}],
                        'id': False,
                        'start': {'dateTime': '2020-01-15T08:00:00+00:00', 'date': None},
                        'end': {'dateTime': '2020-01-15T18:00:00+00:00', 'date': None},
                        'guestsCanModify': is_public,
                        'organizer': {'email': organizer.email, 'self': False} if organizer else False,
                        'summary': 'Event',
                        'reminders': {'useDefault': False, 'overrides': []},
                    }, timeout=3)
                else:
                    self.assertGoogleEventNotInserted()
                    self.assertMailMail(partner, 'sent', author=user_root.partner_id)
