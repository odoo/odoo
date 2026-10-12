# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.exceptions import UserError


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCommon(SelfOrderCommonTest):
    def test_self_order_config_default_user(self):
        self.pos_config.payment_method_ids = self.pos_config.payment_method_ids.filtered(lambda pm: pm.type != 'cash')
        for mode in ("mobile", "consultation", "kiosk"):
            self.pos_config.write({"self_ordering_mode": mode})
            with self.assertRaises(UserError):
                self.pos_config.write({"self_ordering_default_user_id": False})

    def test_self_order_products_sorting_order(self):
        """Test self order products sorting order should follow: favorite, pos_sequence, name"""

        products_data = [
            # product, is_favorite, pos_sequence
            (self.cola, False, 20),
            (self.desk_organizer, True, 20),
            (self.ketchup, False, 5),
            (self.fanta, False, 10),
            (self.free, True, 10),
        ]

        for product, is_favorite, pos_sequence in products_data:
            product.write({
                'is_favorite': is_favorite,
                'pos_sequence': pos_sequence
            })

        for mode in ('mobile', 'kiosk', 'consultation'):
            self.pos_config.write({'self_ordering_mode': mode})
            self.start_tour(self.pos_config._get_self_order_route(), 'test_self_order_products_sorting_order')

    # --- _get_self_order_route ----------------------------------------------------------

    def _create_order(self, **kwargs):
        vals = {
            'session_id': self.pos_config.current_session_id.id,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'amount_paid': 0.0,
            'preset_id': self.in_preset.id,
        }
        vals.update(kwargs)
        return self.env['pos.order'].create(vals)

    def test_get_self_order_route_consultation(self):
        self.pos_config.write({
            'self_ordering_mode': 'consultation',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        route = self.pos_config._get_self_order_route(table_id=self.pos_table_1.id)
        self.assertEqual(route, f"/pos-self/{self.pos_config.id}")

        order = self._create_order()
        route = self.pos_config._get_self_order_route(order=order)
        self.assertEqual(route, f"/pos-self/{self.pos_config.id}")

    def test_get_self_order_route_mobile(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        route = self.pos_config._get_self_order_route()
        self.assertEqual(
            route,
            f"/pos-self/{self.pos_config.id}?access_token={self.pos_config.access_token}",
        )

        route = self.pos_config._get_self_order_route(table_id=self.pos_table_1.id)
        self.assertEqual(
            route,
            f"/pos-self/{self.pos_config.id}"
            f"?access_token={self.pos_config.access_token}"
            f"&table_identifier={self.pos_table_1.identifier}",
        )

        order = self._create_order()
        route = self.pos_config._get_self_order_route(order=order)
        self.assertEqual(
            route,
            f"/pos-self/{self.pos_config.id}"
            f"?access_token={self.pos_config.access_token}"
            f"&order_identifier={order.access_token}",
        )

    def test_get_self_order_route_kiosk(self):
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')

        route = self.pos_config._get_self_order_route(table_id=self.pos_table_1.id)
        self.assertEqual(
            route,
            f"/pos-self/{self.pos_config.id}?access_token={self.pos_config.access_token}",
        )

        order = self._create_order()
        route = self.pos_config._get_self_order_route(order=order)
        self.assertEqual(
            route,
            f"/pos-self/{self.pos_config.id}?access_token={self.pos_config.access_token}",
        )

    # --- get_dynamic_qr_url ----------------------------------------------------------

    def test_get_dynamic_qr_url(self):
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'dynamic_qr',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, '')
        order = self._create_order(table_id=self.pos_table_1.id)

        # Normal case
        url = self.pos_config.get_dynamic_qr_url(order.id)
        self.assertEqual(
            url,
            self.pos_config.get_base_url() + f"/pos-self/{self.pos_config.id}"
            f"?access_token={self.pos_config.access_token}"
            f"&order_identifier={order.access_token}",
        )

        # Wrong mode.
        self.pos_config.self_ordering_mode = 'consultation'
        self.assertFalse(self.pos_config.get_dynamic_qr_url(order.id))
        self.pos_config.self_ordering_mode = 'mobile'

        # Unknown order id.
        self.assertFalse(self.pos_config.get_dynamic_qr_url(order.id + 100000))

        # Order belongs to a different config.
        other_config = self.env['pos.config'].create({'name': 'Other config'})
        order.config_id = other_config.id
        self.assertFalse(self.pos_config.get_dynamic_qr_url(order.id))
        order.config_id = self.pos_config.id

        # Preset not table service.
        order.preset_id = self.out_preset.id
        self.assertFalse(self.pos_config.get_dynamic_qr_url(order.id))

        # No preset at all is still valid.
        order.preset_id = False
        self.assertTrue(self.pos_config.get_dynamic_qr_url(order.id))

        # Order no longer draft.
        order.state = 'paid'
        self.assertFalse(self.pos_config.get_dynamic_qr_url(order.id))
