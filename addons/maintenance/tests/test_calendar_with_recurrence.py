from odoo.tests import HttpCase, tagged
from datetime import datetime, time
from dateutil.relativedelta import relativedelta


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
            'schedule_date': datetime.now() + relativedelta(weeks=-2),
        }, {
            'name': 'wash the car',
            'schedule_date': datetime.now() + relativedelta(weeks=+3),
        }, {
            'name': 'clean the room',
            'schedule_date': datetime.now(),
            'equipment_id': equipment.id,  # necessary for the tour to work with mrp_maintenance installed
            'maintenance_type': 'preventive',
            'recurring_maintenance': True,
            'repeat_until': datetime.now() + relativedelta(days=+8),
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
        Occurences should be locked, drag and drop should have no effect
        """
        self.env['maintenance.team'].create({
            'name': 'the boys',
        })
        requests = self.env['maintenance.request'].create([{
            'name': 'send the mails',
            'schedule_date': datetime.now() + relativedelta(months=-2),
        }, {
            'name': 'wash the car',
            'schedule_date': datetime.now() + relativedelta(months=+1),
        }, {
            'name': 'clean the room',
            'schedule_date': datetime.combine(datetime.now().replace(day=6), time.min.replace(hour=10)),  # 6th of the month at 10 AM
            'maintenance_type': 'preventive',
            'recurring_maintenance': True,
            'repeat_interval': 1,
            'repeat_until': datetime.now() + relativedelta(weeks=+2),
            'repeat_unit': 'week',
            'duration': 1,
        }])
        request = requests[2]

        action = self.env["ir.actions.actions"]._for_xml_id("maintenance.hr_equipment_request_action_cal")
        url = '/web?#action=%s' % (action['id'])
        self.start_tour(url, 'test_drag_and_drop_event_in_calendar', login='admin')

        target_datetime = datetime.combine(datetime.now().replace(day=15), time.min.replace(hour=10))  # 15h of the month at 10 AM
        self.assertEqual(request.schedule_date, target_datetime, "The event modification should update the request")
