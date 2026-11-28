from datetime import date, datetime
from zoneinfo import ZoneInfo

from odoo.addons.http_routing.tests.common import MockRequest
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.website_event.tests.common import TestEventOnlineCommon
from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.tests.common import HttpCase, freeze_time, tagged, users


@tagged('post_install', '-at_install')
class TestWebsiteEventTrack(TestEventOnlineCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['res.config.settings'].write({
            'module_website_event_track_live': True,
        })
        cls.demo_user = mail_new_test_user(
            cls.env,
            name='Demo User',
            login='demo_user',
            email='demo_user@example.com',
            groups='base.group_user',
        )
        cls.event_0.write({'is_published': True})
        cls.track = cls.env['event.track'].create([{
            'name': 'Introduction class',
            'event_id': cls.event_0.id,
            'date': cls.event_0.date_begin,
            'is_published': True,
        }])

    @freeze_time('2020-07-05')
    def test_email_reminder_tour(self):
        """ Check the recovery of the email address of a public user and a logged
        user for the email with track reminders. """
        for user in [self.demo_user, self.env['res.users']]:
            with self.subTest(user=user):
                # Check that the modal to submit an email address for reminders
                # is displayed for public user.
                self.start_tour(f'{self.event_0.website_url}/agenda',
                                'email_reminder_tour',
                                login=user.login)

                mails = self.env['mail.message'].search([
                    ('model', '=', self.track._name),
                    ('res_id', '=', self.track.id),
                    ('subject', '=', f'Add talk reminder: {self.track.name}')
                ]).mail_ids.filtered(lambda m: m.email_to == (user.email or "visitor@odoo.com"))
                # Check that a mail with track reminders has been created with the submitted email address.
                self.assertEqual(len(mails), 1)

    def test_compute_is_one_day(self):
        """Ensure is_one_day is False when both date and date_end are missing."""
        track = self.env['event.track'].create({
            'name': 'Track Without Dates',
            'event_id': self.event_0.id,
        })
        self.assertFalse(track.is_one_day, "Expected Is One Day to be False when no date is set.")
        self.assertTrue(track.name, "Track name should be correctly set.")
        self.assertTrue(track.event_id, "Track should be linked to the correct event.")

    def test_compute_track_time_data(self):
        """Test that _compute_track_time_data sets defaults when no date or date_end is set."""
        track = self.env['event.track'].create({
            'name': 'Track Without Date Info',
            'event_id': self.event_0.id,
        })
        self.assertFalse(track.is_track_live, "Track should not be live without date.")
        self.assertFalse(track.is_track_soon, "Track should not be marked as soon without date.")
        self.assertFalse(track.is_track_today, "Track should not be marked as today without date.")
        self.assertFalse(track.is_track_upcoming, "Track should not be upcoming without date.")
        self.assertFalse(track.is_track_done, "Track should not be done without date.")
        self.assertEqual(track.track_start_relative, 0, "Track start relative should be 0.")
        self.assertEqual(track.track_start_remaining, 0, "Track start remaining should be 0.")

    @users('user_eventmanager')
    def test_website_event_track_agenda_times(self):
        """Check that event tracks' times displayed in the agenda are converted using the event's time zone and
        not the one of the active user and that they are formatted according to the user language's time format."""
        self.env.user.tz = 'America/New_York'  # UTC-4
        self.event_0.date_tz = 'Asia/Riyadh'  # UTC+3
        location = self.env['event.track.location'].create({'name': 'Main Stage'})
        track = self.env['event.track'].create({
            'date': datetime(2020, 7, 5, 23),
            'duration': 1,
            'event_id': self.event_0.id,
            'is_published': True,
            'location_id': location.id,
            'name': 'Talk at night',
        })
        lang = self.env['res.lang']._lang_get(self.env.user.lang)

        for time_format, formatted_time, start_date, end_date in [
            ('%I:%M:%S %p', '02:00 AM', '02:00 AM', '03:00 AM'),
            ('%H:%M:%S', '02:00', '02:00', '03:00'),
        ]:
            lang.sudo().time_format = time_format
            with self.subTest(formatted_time=formatted_time, start_date=start_date, end_date=end_date), MockRequest(self.env):
                time_slots = EventTrackController()._prepare_calendar_values(self.event_0)['time_slots']

                # Check that the track is displayed at its time converted using the event's time zone and the format of
                # its times is the one of the user language.
                tomorrow_utc_slots = time_slots[date(2020, 7, 6)]
                track_time_slot = tomorrow_utc_slots[datetime(2020, 7, 6, 2, tzinfo=ZoneInfo('Asia/Riyadh'))]
                self.assertEqual(track_time_slot['formatted_time'], formatted_time)
                self.assertEqual(track_time_slot[location][track]['start_date'], start_date)
                self.assertEqual(track_time_slot[location][track]['end_date'], end_date)

                # Check that the track is not displayed at its time converted using the user's time zone.
                self.assertNotIn(
                    datetime(2020, 7, 5, 19, tzinfo=ZoneInfo('America/New_York')),
                    time_slots[date(2020, 7, 5)]
                )
