import odoo.tests
from odoo.addons.google_address_autocomplete.controllers.google_address_autocomplete import AutoCompleteController
from unittest.mock import patch
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged('post_install', '-at_install')
class TestSelfOrderPreset(SelfOrderCommonTest):
    def setUp(self):
        super().setUp()
        # Set up Google Places API key for address autocomplete tests
        self.env["ir.config_parameter"].sudo().set_str(
            "google_address_autocomplete.google_places_api_key",
            "test_api_key_for_autocomplete"
        )
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

        with patch(
            "odoo.addons.pos_self_order.controllers.orders.PosSelfOrderController._check_delivery_address_for_partner",
            side_effect=[
                None,  # First call: address is valid
                {"type": "delivery", "message": "Delivery isn't available for this address."},  # Second call: too far
            ],
        ), patch.object(
            AutoCompleteController,
            '_perform_place_search',
            return_value={
                "results": [
                    {
                        "formatted_address": "Rue du Bronx 90, 9999 New York",
                        "google_place_id": "test_place_id",
                    }
                ],
                "session_id": "test_session",
            },
        ), patch.object(
            AutoCompleteController,
            '_perform_complete_place_search',
            return_value={
                "street": "Rue du Bronx",
                "number": "90",
                "formatted_street_number": "Rue du Bronx 90",
                "zip": "9999",
                "city": "New York",
                "country": [self.env.ref("base.be").id, "Belgium"],
                "state": False,
            },
        ):
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
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
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
                'dayofweek': str(day),
                'hour_from': 0,
                'hour_to': 24,
            }) for day in range(0, 6)],
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
