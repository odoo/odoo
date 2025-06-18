from datetime import datetime, date
from freezegun import freeze_time

from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.tests import tagged, users


@tagged('mail_activity_mixin', 'mail_activity', 'post_install', '-at_install')
class TestCalendarActivity(ActivityScheduleCase):

    @users('employee')
    def test_synchronize_activity_timezone(self):
        activity_type = self.activity_type_todo.with_user(self.env.user)

        with freeze_time(datetime(2025, 6, 19, 12, 44, 00)):
            activity = self.env['mail.activity'].create({
                'activity_type_id': activity_type.id,
                'res_model_id': self.env['ir.model']._get_id('res.partner'),
                'res_id': self.env['res.partner'].create({'name': 'A Partner'}).id,
                'summary': 'Meeting with partner',
            })
        self.assertEqual(activity.date_deadline, date(2025, 6, 19))

        with freeze_time(datetime(2025, 6, 19, 12, 44, 00)):
            calendar_event = self.env['calendar.event'].create({
                'activity_ids': [(6, 0, activity.ids)],
                'name': 'Meeting with partner',
                'start': datetime(2025, 6, 21, 21, 0, 0),
                'stop': datetime(2025, 6, 22, 0, 0, 0),
            })
        # Check output in UTC
        self.assertEqual(activity.date_deadline, date(2025, 6, 21))

        # Check output in the user's tz
        # write on the event to trigger sync of activities
        calendar_event.with_context({'tz': 'Australia/Brisbane'}).write({
            'start': datetime(2025, 6, 27, 21, 0, 0),
        })
        self.assertEqual(activity.date_deadline, date(2025, 6, 28),
                         'Next day due to timezone')

        # now change from activity, timezone should be taken into account when
        # converting into UTC for event
        activity.with_context({'tz': 'Australia/Brisbane'}).date_deadline = date(2025, 6, 30)
        self.assertEqual(calendar_event.start, datetime(2025, 6, 29, 21, 0, 0),
                         'Should apply diff in days, taking into account timezone')

    def test_synchronize_activity_timezone_allday(self):
        # Covers use case of commit eef4c3b48bcb4feac028bf640b545006dd0c9b91
        # Also, read the comment in the code at calendar.event._inverse_dates
        activity_type = self.activity_type_todo.with_user(self.env.user)

        with freeze_time(datetime(2025, 6, 19, 12, 44, 00)):
            activity = self.env['mail.activity'].create({
                'activity_type_id': activity_type.id,
                'res_id': self.env['res.partner'].create({'name': 'A Partner'}).id,
                'res_model_id': self.env['ir.model']._get_id('res.partner'),
                'summary': 'Meeting with partner',
            })
        self.assertEqual(activity.date_deadline, date(2025, 6, 19))

        with freeze_time(datetime(2025, 6, 19, 12, 44, 00)):
            calendar_event = self.env['calendar.event'].create({
                'activity_ids': [(6, False, activity.ids)],
                'allday': True,
                'name': 'All Day',
                'start': datetime(2025, 6, 21, 0, 0, 0),
                'start_date': date(2025, 6, 21),
                'stop': datetime(2025, 6, 23, 0, 0, 0),
                'stop_date': date(2025, 6, 23),
            })
        # Check output in UTC
        self.assertEqual(activity.date_deadline, date(2025, 6, 21))

        # Check output in the user's tz
        # write on the event to trigger sync of activities
        calendar_event.with_context({'tz': 'Pacific/Honolulu'}).write({
            'start': datetime(2025, 6, 22, 0, 0, 0),
            'start_date': date(2025, 6, 22),
        })
        self.assertEqual(calendar_event.start, datetime(2025, 6, 22, 8, 0, 0),
                         'Calendar datetime updated with timezone')
        self.assertEqual(activity.date_deadline, date(2025, 6, 22),
                         'Same day, as taking all day, do not care about timezone')

        # now change from activity, timezone should not be taken into account
        # and just update the starting day
        activity.with_context({'tz': 'Australia/Brisbane'}).date_deadline = date(2025, 6, 30)
        self.assertEqual(calendar_event.start, datetime(2025, 6, 30, 8, 0, 0),
                         'Just apply days diff, timezone do not matter')
        self.assertEqual(calendar_event.start_date, date(2025, 6, 30),
                         'Just apply days diff, timezone do not matter')
