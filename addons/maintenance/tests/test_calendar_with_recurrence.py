from odoo.tests import HttpCase, tagged
from datetime import timedelta, date, datetime


@tagged('post_install', '-at_install')
class TestCalendarWithRecurrence(HttpCase):

    def test_dblclick_event_from_calendar(self):
        """Make sure double clicking on an event and its recurrences lead to the correct record"""
        self.env['maintenance.team'].create({
            'name': 'the boys',
        })
        equipment = self.env['maintenance.equipment'].create({
            'name': 'room'
        })
        requests = self.env['maintenance.request'].create([{
            'name': 'send the mails',
            'schedule_date': datetime.now() - timedelta(weeks=2),
        }, {
            'name': 'wash the car',
            'schedule_date': datetime.now() + timedelta(weeks=3),
        }, {
            'name': 'clean the room',
            'schedule_date': datetime.now(),
            'equipment_id': equipment.id,  # necessary for the tour to work with mrp_maintenance installed
            'maintenance_type': 'preventive',
            'recurring_maintenance': True,
            'repeat_until': datetime.now() + timedelta(days=8),
            'repeat_interval': 1,
            'repeat_unit': 'day',
            'duration': 1,
        }])
        request = requests[2]

        action = self.env["ir.actions.actions"]._for_xml_id("maintenance.hr_equipment_request_action_cal")
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, 'test_dblclick_event_from_calendar', login='admin')

        self.assertEqual(request.name, 'make your bed', "The event modification should update the request")
        self.assertEqual(request.duration, 2, "The event modification should update the request")

    def test_drag_and_drop_calendar_event(self):
        """
        Make sure dragging and dropping an event changes the correct record
        Reccurences should be locked, drag and drop should have no effect
        """
        self.env['maintenance.team'].create({
            'name': 'the boys',
        })
        requests = self.env['maintenance.request'].create([{
            'name': 'send the mails',
            'schedule_date': datetime.now() - timedelta(weeks=2),
        }, {
            'name': 'wash the car',
            'schedule_date': datetime.now() + timedelta(weeks=1),
        }, {
            'name': 'clean the room',
            'schedule_date': datetime.combine(date.today(), (datetime.min + timedelta(hours=10)).time()),  # today at 10.00 AM
            'maintenance_type': 'preventive',
            'recurring_maintenance': True,
            'repeat_interval': 1,
            'repeat_until': datetime.now() + timedelta(days=2),
            'repeat_unit': 'day',
            'duration': 1,
        }])
        request = requests[2]

        action = self.env["ir.actions.actions"]._for_xml_id("maintenance.hr_equipment_request_action_cal")
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, 'test_drag_and_drop_event_in_calendar', login='admin')

        today_as_weekday = (date.today().weekday() + 1) % 7  # Sunday is the first day of the week in the calendar
        today_to_wednesday = 3 - today_as_weekday  # difference between Wednesday and today
        target_datetime = datetime.combine(
            date.today() + timedelta(days=today_to_wednesday),
            (datetime.min + timedelta(hours=13.25)).time()
        )  # this Wednesday at 1.15 PM
        self.assertEqual(request.schedule_date, target_datetime, "The event modification should update the request")
