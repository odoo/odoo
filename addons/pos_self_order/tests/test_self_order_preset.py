import pytz
from datetime import datetime, timedelta

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderPreset(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()
        self.preset_dine_in = self.env['pos.preset'].create({
            'name': 'Dine in',
            'available_in_self': True,
            'service_at': 'table',
        })
        self.preset_takeaway = self.env['pos.preset'].create({
            'name': 'Takeaway',
            'available_in_self': True,
            'service_at': 'counter',
            'identification': 'name',
        })
        self.preset_delivery = self.env['pos.preset'].create({
            'name': 'Delivery',
            'available_in_self': True,
            'service_at': 'delivery',
            'identification': 'address',
        })
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'use_presets': True,
            'default_preset_id': self.preset_dine_in.id,
            'available_preset_ids': [(6, 0, [self.preset_takeaway.id, self.preset_delivery.id])],
        })

    def test_preset_dine_in_tour(self):
        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "background_color": 'rgb(249,250,251)',
            "table_ids": [(0, 0, {
                "table_number": 1,
            })],
        })
        self.pos_config.write({
            "floor_ids": [(6, 0, [floor.id])],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route(floor.table_ids[0].id)
        self.start_tour(self_route, "self_order_preset_dine_in_tour")

    def test_preset_takeaway_tour(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_preset_takeaway_tour")
        self.assertEqual("Dr Dre", self.env["pos.order"].search([], limit=1, order="id desc").floating_order_name)

    def test_preset_delivery_tour(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_preset_delivery_tour")

        last_order = self.env["pos.order"].search([], limit=1, order="id desc")
        self.assertEqual(last_order.partner_id.name, 'Dr Dre')
        self.assertEqual(last_order.partner_id.email, 'dre@dr.com')
        self.assertEqual(last_order.partner_id.street, 'Rue du Bronx 90')
        self.assertEqual(last_order.partner_id.zip, '9999')
        self.assertEqual(last_order.partner_id.city, 'New York')
        self.assertEqual(last_order.partner_id.phone, '+32490904390')

    def test_preset_with_slot_tour(self):
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Takeaway',
            'attendance_ids': [(0, 0, {
                'name': 'Takeaway',
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
                'day_period': 'morning',
            }) for day in range(0, 6)],
        })
        self.preset_takeaway.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_preset_slot_tour")
        last_order = self.env["pos.order"].search([], limit=1, order="id desc")
        self.assertEqual(last_order.floating_order_name, 'Dr Dre')
        self.assertNotEqual(last_order.preset_time, False)

    def test_slot_limit_orders(self):
        """
        Tests that when a slot reached it's limit capacity, it is not shown
        in the selector anymore.
        """
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Takeaway',
            'attendance_ids': [(0, 0, {
                'name': 'Takeaway',
                'dayofweek': '0',
                'hour_from': 0,
                'hour_to': 24,
                'day_period': 'morning',
            })],
        })
        self.preset_takeaway.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar,
            'slots_per_interval': 1,
            'interval_time': 20,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_slot_limit_orders")

    def test_slot_time_off(self):
        """
        Tests that when a slot falls within a resource calendar's leave / time off,
        the slot is marked as fully used in the return values of get_available_slots,
        while slots outside the leave window remain available.
        """
        resource_calendar = self.env['resource.calendar'].create({
            'name': 'Takeaway',
            'attendance_ids': [(0, 0, {
                'name': 'Takeaway',
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
                'day_period': 'morning',
            }) for day in range(7)],
        })

        capacity = 5
        interval = 20
        self.preset_takeaway.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar.id,
            'slots_per_interval': capacity,
            'interval_time': interval,
        })

        tz = pytz.timezone(resource_calendar.tz or self.env.user.tz or 'UTC')
        now_tz = datetime.now(tz)
        tomorrow = (now_tz + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        leave_start = tomorrow.replace(hour=10)
        leave_end = tomorrow.replace(hour=12)

        leave_start_utc = leave_start.astimezone(pytz.utc).replace(tzinfo=None)
        leave_end_utc = leave_end.astimezone(pytz.utc).replace(tzinfo=None)

        self.env['resource.calendar.leaves'].create({
            'name': 'Time Off',
            'calendar_id': resource_calendar.id,
            'date_from': leave_start_utc,
            'date_to': leave_end_utc,
        })

        res = self.preset_takeaway.get_available_slots()
        usage = res['usage_utc']

        # Generate expected blocked slots within the leave window [10:00, 12:00)
        blocked_slots = []
        slot = leave_start
        while slot < leave_end:
            slot_utc_str = slot.astimezone(pytz.utc).replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
            blocked_slots.append(slot_utc_str)
            slot += timedelta(minutes=interval)

        self.assertTrue(len(blocked_slots) > 0, "There should be at least one blocked slot within the leave window")

        for slot_key in blocked_slots:
            self.assertIn(slot_key, usage, f"Slot {slot_key} should be present in usage (blocked by leave)")
            self.assertEqual(
                len(usage[slot_key]), capacity,
                f"Slot {slot_key} should be fully blocked with {capacity} dummy entries"
            )

        # Verify that slots just outside the leave window are NOT blocked
        slot_before_leave = (leave_start - timedelta(minutes=interval)).astimezone(pytz.utc).replace(tzinfo=None)
        slot_before_key = slot_before_leave.strftime("%Y-%m-%d %H:%M:%S")
        if slot_before_key in usage:
            self.assertNotEqual(
                len(usage[slot_before_key]), capacity,
                f"Slot {slot_before_key} (before leave) should not be fully blocked"
            )

        slot_after_leave = leave_end.astimezone(pytz.utc).replace(tzinfo=None)
        slot_after_key = slot_after_leave.strftime("%Y-%m-%d %H:%M:%S")
        if slot_after_key in usage:
            self.assertNotEqual(
                len(usage[slot_after_key]), capacity,
                f"Slot {slot_after_key} (after leave) should not be fully blocked"
            )
