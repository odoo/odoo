import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderPreset(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()
        self.setup_test_self_presets()

    def test_preset_eat_in_tour(self):
        self.setup_self_floor_and_table()
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("self_order_preset_eat_in_tour")

    def test_preset_takeaway_tour(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("self_order_preset_takeaway_tour")
        self.assertEqual("Dr Dre", self.env["pos.order"].search([], limit=1, order="id desc").floating_order_name)

    def test_preset_delivery_tour(self):
        self.desk_pad.list_price = 0
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("self_order_preset_delivery_tour")

        last_order = self.env["pos.order"].search([], limit=1, order="id desc")
        self.assertEqual(last_order.partner_id.name, 'Dr Dre')
        self.assertEqual(last_order.partner_id.street, 'Rue du Bronx 90')
        self.assertEqual(last_order.partner_id.zip, '9999')
        self.assertEqual(last_order.partner_id.city, 'New York')
        self.assertEqual(last_order.partner_id.phone, '0490 90 43 90')

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
        self.out_preset.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_pos_self_tour("self_order_preset_slot_tour")
        last_order = self.env["pos.order"].search([], limit=1, order="id desc")
        self.assertEqual(last_order.floating_order_name, 'Dr Dre')
        self.assertNotEqual(last_order.preset_time, False)
