from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest

import odoo


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderSecurity(SelfOrderCommonTest):

    def test_self_order_create_price_on_backend(self):
        self.pos_config.write({
            'takeaway': True,
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_order_create_price_on_backend")

    def test_self_order_create_price_on_backend_combo(self):
        setup_product_combo_items(self)
        self.env["product.combo.item"].create(
            {
                "product_id": self.desk_organizer.id,
                "extra_price": 0,
                "combo_id": self.desk_accessories_combo.id,
            }
        )
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'counter',
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "self_order_create_price_on_backend_combo_correct")
        self.start_tour(self_route, "self_order_create_price_on_backend_combo_modified")
