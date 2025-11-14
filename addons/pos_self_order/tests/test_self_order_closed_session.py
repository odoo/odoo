import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderClosedSession(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()
        self.preset_eat_in = self.env['pos.preset'].create({
            'name': 'Eat in',
            'available_in_self': True,
            'service_at': 'table',
        })
        self.preset_takeaway = self.env['pos.preset'].create({
            'name': 'Takeaway',
            'available_in_self': True,
            'service_at': 'counter',
            'identification': 'name',
        })
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
        self.preset_takeaway.write({
            'use_timing': True,
            'resource_calendar_id': resource_calendar,
        })

        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'use_presets': True,
            'default_preset_id': self.preset_eat_in.id,
            'available_preset_ids': [(6, 0, [self.preset_takeaway.id])],
        })

    def test_consultation_session_opened_several_presets(self):
        self.pos_config.self_ordering_mode = 'consultation'

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_closed_session.consultation_session_opened_several_presets")

    def test_mobile_session_closed_one_eatin_preset(self):
        self.pos_config.available_preset_ids = [(3, self.preset_takeaway.id)]

        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_closed_session.mobile_session_closed_one_eatin_preset")

    def test_mobile_session_closed_several_presets(self):
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_closed_session.mobile_session_closed_several_presets")

        order = self.env['pos.order'].search([], limit=1, order='id desc')
        self.assertEqual(order.preset_id.id, self.preset_takeaway.id)
        self.assertEqual(order.floating_order_name, 'Self-Order-1')
        self.assertFalse(order.session_id)
        self.assertFalse(order.pos_reference)
        self.assertEqual(order.tracking_number, "__self_order_no_session__")
        self.assertFalse(order.sequence_number)

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        order = self.env['pos.order'].search([('id', '=', order.id)])
        self.assertEqual(order.preset_id.id, self.preset_takeaway.id)
        self.assertEqual(order.floating_order_name, 'Self-Order-1')
        self.assertEqual(order.session_id.id, self.pos_config.current_session_id.id)
        self.assertTrue(order.pos_reference.endswith("-00001"))
        self.assertEqual(order.tracking_number, "S001")
        self.assertEqual(order.sequence_number, 1)

    def test_mobile_session_opening_control_several_presets(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_closed_session.mobile_session_opening_control_several_presets")

        order = self.env['pos.order'].search([], limit=1, order='id desc')
        self.assertEqual(order.preset_id.id, self.preset_takeaway.id)
        self.assertEqual(order.floating_order_name, 'Self-Order-1')
        self.assertEqual(order.session_id.id, self.pos_config.current_session_id.id)
        self.assertTrue(order.pos_reference.endswith("-00001"))
        self.assertEqual(order.tracking_number, "S001")
        self.assertEqual(order.sequence_number, 1)

        previous_session_id = order.session_id.id
        self.pos_config.current_session_id.set_opening_control(0, "")

        order = self.env['pos.order'].search([('id', '=', order.id)])
        self.assertEqual(order.preset_id.id, self.preset_takeaway.id)
        self.assertEqual(order.floating_order_name, 'Self-Order-1')
        self.assertEqual(order.session_id.id, self.pos_config.current_session_id.id)
        self.assertEqual(order.session_id.id, previous_session_id)
        self.assertTrue(order.pos_reference.endswith("-00001"))
        self.assertEqual(order.tracking_number, "S001")
        self.assertEqual(order.sequence_number, 1)

    def test_mobile_session_opened_several_presets(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_closed_session.mobile_session_opened_several_presets")

        order = self.env['pos.order'].search([], limit=1, order='id desc')
        self.assertEqual(order.preset_id.id, self.preset_takeaway.id)
        self.assertEqual(order.floating_order_name, 'Self-Order-1')
        self.assertEqual(order.session_id.id, self.pos_config.current_session_id.id)
        self.assertTrue(order.pos_reference.endswith("-00001"))
        self.assertEqual(order.tracking_number, "S001")
        self.assertEqual(order.sequence_number, 1)

    def test_kiosk_session_opened_several_presets(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_order_closed_session.kiosk_session_opened_several_presets")

        order = self.env['pos.order'].search([], limit=1, order='id desc')
        self.assertEqual(order.preset_id.id, self.preset_takeaway.id)
        self.assertEqual(order.floating_order_name, 'K001')
        self.assertEqual(order.session_id.id, self.pos_config.current_session_id.id)
        self.assertTrue(order.pos_reference.endswith("-00001"))
        self.assertEqual(order.tracking_number, "K001")
        self.assertEqual(order.sequence_number, 1)
