from datetime import datetime, time

from dateutil.relativedelta import relativedelta

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestCalendarWithRecurrence(HttpCase):
    def test_dblclick_event_from_calendar(self):
        """Make sure double clicking on an event and its recurrences lead to the correct record"""
        self.env["team.team"].create(
            {
                "use_maintenance": True,
                "name": "the boys",
            }
        )
        self.env["maintenance.order"].create(
            [
                {
                    "name": "send the mails",
                    "date_scheduled_start": datetime.now() + relativedelta(weeks=-2),
                },
                {
                    "name": "wash the car",
                    "date_scheduled_start": datetime.now() + relativedelta(weeks=+3),
                },
            ]
        )
        plan = self.env["maintenance.plan"].create(
            {
                "name": "clean the room",
                "date_first_occurrence": datetime.now(),
                "repeat_type": "until",
                "repeat_until": datetime.now() + relativedelta(days=+8),
                "repeat_interval": 1,
                "repeat_unit": "day",
            }
        )
        order = plan.order_ids

        url = "/odoo/action-maintenance.maintenance_order_action_cal"
        self.start_tour(url, "test_dblclick_event_from_calendar", login="admin")

        self.assertEqual(
            order.name,
            "make your bed",
            "The event modification should update the order",
        )
        self.assertAlmostEqual(
            order.duration, 2, 2, "The event modification should update the order"
        )

    def test_drag_and_drop_calendar_event(self):
        """
        Make sure dragging and dropping an event changes the correct record
        Occurences should be locked, drag and drop should have no effect
        """
        self.env["team.team"].create(
            {
                "use_maintenance": True,
                "name": "the boys",
            }
        )
        self.env["maintenance.order"].create(
            [
                {
                    "name": "send the mails",
                    "date_scheduled_start": datetime.now() + relativedelta(months=-2),
                },
                {
                    "name": "wash the car",
                    "date_scheduled_start": datetime.now() + relativedelta(months=+1),
                },
            ]
        )
        plan = self.env["maintenance.plan"].create(
            {
                "name": "clean the room",
                "date_first_occurrence": datetime.combine(
                    datetime.now().replace(day=6), time.min.replace(hour=10)
                ),  # 6th of the month at 10 AM
                "repeat_interval": 1,
                "repeat_type": "until",
                "repeat_until": datetime.now() + relativedelta(weeks=+2),
                "repeat_unit": "week",
            }
        )
        order = plan.order_ids

        url = "/odoo/action-maintenance.maintenance_order_action_cal"
        self.start_tour(url, "test_drag_and_drop_event_in_calendar", login="admin")

        target_datetime = datetime.combine(
            datetime.now().replace(day=15), time.min.replace(hour=10)
        )  # 15h of the month at 10 AM
        self.assertEqual(
            order.date_scheduled_start,
            target_datetime,
            "The event modification should update the order",
        )
