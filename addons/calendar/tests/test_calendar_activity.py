from datetime import datetime, date, timedelta
from freezegun import freeze_time

from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.tests import tagged, users


@tagged('mail_activity_mixin', 'mail_activity', 'post_install', '-at_install')
class TestCalendarActivity(ActivityScheduleCase):

    def test_event_activity(self):
        # ensure meeting activity type exists
        meeting_act_type = self.env['mail.activity.type'].search([('category', '=', 'meeting')], limit=1)
        if not meeting_act_type:
            meeting_act_type = self.env['mail.activity.type'].create({
                'name': 'Meeting Test',
                'category': 'meeting',
            })

        # have a test model inheriting from activities
        test_record = self.env['res.partner'].create({
            'name': 'Test',
        })
        now = datetime.now()

        # test with escaping
        test_name, test_description, test_description2 = 'Test-Meeting', 'Test-Description', 'Test & <br> Description'
        test_note, test_note2 = '<p>Test-Description</p>', '<p>Test &amp; <br> Description</p>'

        # create using default_* keys
        test_event = self.env['calendar.event'].with_user(self.user_employee).with_context(
            default_res_model=test_record._name,
            default_res_id=test_record.id,
        ).create({
            'name': test_name,
            'description': test_description,
            'start': now + timedelta(days=-1),
            'stop': now + timedelta(hours=2),
            'user_id': self.env.user.id,
        })
        self.assertEqual(test_event.res_model, test_record._name)
        self.assertEqual(test_event.res_id, test_record.id)
        self.assertEqual(len(test_record.activity_ids), 1)
        self.assertEqual(test_record.activity_ids.summary, test_name)
        self.assertEqual(test_record.activity_ids.note, test_note)
        self.assertEqual(test_record.activity_ids.user_id, self.env.user)
        self.assertEqual(test_record.activity_ids.date_deadline, (now + timedelta(days=-1)).date())

        # updating event should update activity
        test_event.write({
            'name': '%s2' % test_name,
            'description': test_description2,
            'start': now + timedelta(days=-2),
            'user_id': self.user_employee.id,
        })

        activity = test_record.activity_ids[0]
        self.assertEqual(activity.summary, '%s2' % test_name)
        self.assertEqual(activity.note, test_note2)
        self.assertEqual(activity.user_id, self.user_employee)
        self.assertEqual(activity.date_deadline, (now + timedelta(days=-2)).date())

        # deleting meeting should delete its activity
        test_record.activity_ids.unlink()
        self.assertEqual(self.env['calendar.event'], self.env['calendar.event'].search([('name', '=', test_name)]))

        # create using active_model keys
        test_event = self.env['calendar.event'].with_user(self.user_employee).with_context(
            active_model=test_record._name,
            active_id=test_record.id,
        ).create({
            'name': test_name,
            'description': test_description,
            'start': now + timedelta(days=-1),
            'stop': now + timedelta(hours=2),
            'user_id': self.env.user.id,
        })
        self.assertEqual(test_event.res_model, test_record._name)
        self.assertEqual(test_event.res_id, test_record.id)
        self.assertEqual(len(test_record.activity_ids), 1)

    def test_activity_event_multiple_meetings(self):
        # Creating multiple meetings from an activity creates additional activities
        # ensure meeting activity type exists
        meeting_act_type = self.env.ref('mail.mail_activity_data_meeting')

        # have a test model inheriting from activities
        test_record = self.env['res.partner'].create({
            'name': 'Test',
        })

        activity_1 = self.env['mail.activity'].create({
            'summary': 'Meeting 1 with partner',
            'activity_type_id': meeting_act_type.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': test_record.id,
        })

        # default usage in successive create
        event_1_1 = self.env['calendar.event'].with_context(default_activity_ids=[(6, 0, activity_1.ids)]).create({
            'name': 'Meeting 1',
            'start': datetime(2025, 3, 10, 17),
            'stop': datetime(2025, 3, 10, 22),
        })
        self.assertEqual(event_1_1.activity_ids, activity_1)
        self.assertEqual(activity_1.calendar_event_id, event_1_1)
        self.assertEqual(activity_1.date_deadline, date(2025, 3, 10))
        event_1_2 = self.env['calendar.event'].with_context(default_activity_ids=[(6, 0, activity_1.ids)]).create({
            'name': 'Meeting 2',
            'start': datetime(2025, 3, 12, 17),
            'stop': datetime(2025, 3, 12, 22),
        })
        self.assertFalse(event_1_1.activity_ids, 'Changes activity ownership')
        self.assertEqual(event_1_2.activity_ids, activity_1, 'Changes activity ownership')
        self.assertEqual(activity_1.calendar_event_id, event_1_2)
        self.assertEqual(activity_1.date_deadline, date(2025, 3, 12))

        activity_2 = self.env['mail.activity'].create({
            'summary': 'Meeting 2 with partner',
            'activity_type_id': meeting_act_type.id,
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': test_record.id,
        })
        existing_activities = self.env['mail.activity'].search([])

        # specific action that creates activities instead of replacing
        calendar_action = activity_2.with_context(default_res_model='res.partner', default_res_id=test_record.id).action_create_calendar_event()
        event_2_1 = self.env['calendar.event'].with_context(calendar_action['context']).create({
            'name': 'Meeting 1',
            'start': datetime(2025, 4, 10, 17),
            'stop': datetime(2025, 4, 10, 22),
        })
        self.assertEqual(event_2_1.activity_ids, activity_2)
        self.assertEqual(activity_2.calendar_event_id, event_2_1)
        self.assertEqual(activity_2.date_deadline, date(2025, 4, 10))

        event_2_2 = self.env['calendar.event'].with_context(calendar_action['context']).create({
            'name': 'Meeting 2',
            'start': datetime(2025, 4, 11, 17),
            'stop': datetime(2025, 4, 11, 22),
        })
        new_existing_activities = self.env['mail.activity'].search([])
        new_activity = new_existing_activities - existing_activities
        self.assertEqual(event_2_1.activity_ids, activity_2, "Event 1's activity should still be the first activity")
        self.assertEqual(activity_2.calendar_event_id, event_2_1, "The first activity's event should still be event 1")

        self.assertEqual(len(new_activity), 1, "1 more activity record should have been created (by event 2)")
        self.assertEqual(event_2_2.activity_ids, new_activity, "Event 2's activity should not be the first activity")
        self.assertEqual(event_2_2.activity_ids.activity_type_id, activity_2.activity_type_id, "Event 2's activity should be the same activity type as the first activity")
        self.assertEqual(test_record.activity_ids, activity_1 + activity_2 + new_activity, "Resource record should now have all activities")

    def test_event_activity_user_sync(self):
        # ensure phonecall activity type exists
        activty_type = self.env['mail.activity.type'].create({
            'name': 'Call',
            'category': 'phonecall'
        })
        activity = self.env['mail.activity'].create({
            'summary': 'Call with Demo',
            'activity_type_id': activty_type.id,
            'note': 'Schedule call with Admin',
            'res_model_id': self.env['ir.model']._get_id('res.partner'),
            'res_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'user_id': self.user_employee.id,
        })
        action_context = activity.action_create_calendar_event().get('context', {})
        event_from_activity = self.env['calendar.event'].with_context(action_context).create({
            'start': '2022-07-27 14:30:00',
            'stop': '2022-07-27 16:30:00',
        })
        # Check that assignation of the activity hasn't changed, and event is having
        # correct values set in attendee and organizer related fields
        self.assertEqual(activity.user_id, self.user_employee)
        self.assertEqual(event_from_activity.partner_ids, activity.user_id.partner_id)
        self.assertEqual(event_from_activity.attendee_ids.partner_id, activity.user_id.partner_id)
        self.assertEqual(event_from_activity.user_id, activity.user_id)

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
