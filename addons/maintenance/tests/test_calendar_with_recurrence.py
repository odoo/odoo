from odoo.tests import HttpCase, tagged
from odoo.tools.float_utils import float_compare
from datetime import timedelta, date, datetime


@tagged('post_install', '-at_install')
class TestCalendarWithRecurrence(HttpCase):

    def test_dblclick_event_from_calendar(self):
        self.env['maintenance.team'].create({
            'name': 'the boys',
        })
        equipment = self.env['maintenance.equipment'].create({
            'name': 'room'
        })
        self.env['maintenance.request'].create({
            'name': 'send the mails',
            'schedule_date': datetime.today() - timedelta(weeks=2),
        })
        request = self.env['maintenance.request'].create({
            'name': 'clean the room',
            'schedule_date': datetime.combine(date.today(), (datetime.min + timedelta(hours=10)).time()),  # today at 10.00 AM
            'equipment_id': equipment.id,  # necessary for the tour to work with mrp_maintenance installed
            'maintenance_type': 'preventive',
            'recurring_maintenance': True,
            'repeat_interval': 1,
            'repeat_unit': 'day',
            'duration': 1,
        })
        self.env['maintenance.request'].create({
            'name': 'wash the car',
            'schedule_date': datetime.today() + timedelta(weeks=1),
        })

        # The event should have a different id from the record
        self.assertNotEqual(request.id, 1)

        url = '/odoo/action-maintenance.hr_equipment_request_action_cal'
        self.start_tour(url, 'test_dblclick_event_from_calendar', login='admin')

        self.assertEqual(request.name, 'make your bed')
        self.assertEqual(float_compare(request.duration, 2, 0), 0)

    def test_drag_and_drop_calendar_event(self):
        self.env['maintenance.team'].create({
            'name': 'the boys',
        })
        self.env['maintenance.request'].create({
            'name': 'send the mails',
            'schedule_date': datetime.today() - timedelta(weeks=2),
        })
        request = self.env['maintenance.request'].create({
            'name': 'clean the room',
            'schedule_date': datetime.combine(date.today(), (datetime.min + timedelta(hours=10)).time()),  # today at 10.00 AM
            'maintenance_type': 'preventive',
            'recurring_maintenance': True,
            'repeat_interval': 1,
            'repeat_unit': 'day',
            'duration': 1,
        })
        self.env['maintenance.request'].create({
            'name': 'wash the car',
            'schedule_date': datetime.today() + timedelta(weeks=1),
        })

        # The event should have a different id from the record
        self.assertNotEqual(request.id, 1)

        url = '/odoo/action-maintenance.hr_equipment_request_action_cal'
        self.start_tour(url, 'test_drag_and_drop_event_in_calendar', login='admin')

        today_as_weekday = (date.today().weekday() + 1) % 7  # Sunday is the first day of the week in the calendar
        today_to_wednesday = 3 - today_as_weekday  # difference between Wednesday and today
        target_datetime = datetime.combine(
            date.today() + timedelta(days=today_to_wednesday),
            (datetime.min + timedelta(hours=13)).time()
        )  # this Wednesday at 1.15 PM
        self.assertEqual(request.schedule_date, target_datetime)
