# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest

from odoo.exceptions import UserError


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCommon(SelfOrderCommonTest):
    def test_self_order_common(self):
        self.pos_config.write({
            'takeaway': True,
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_takeaway': True,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
        })

        self.pos_admin.groups_id += self.env.ref('account.group_account_invoice')
        self_route = self.pos_config._get_self_order_route()

        # Verify behavior when self Order is closed
        self.start_tour(self_route, "self_order_is_close")

    def test_self_order_consultation_open(self):
        """Verify than when the pos is open and self ordering is set to consultation the banner isn't shown"""
        self.pos_config.write({'self_ordering_mode': 'consultation'})

        self_route = self.pos_config._get_self_order_route()

        # Verify behavior when self Order is opened
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self.start_tour(self_route, "self_order_is_open_consultation")

    def test_self_order_pos_closed(self):
        """
        Verify than when the pos is closed and self ordering is set to mobile, consultation or kiosk,
        we can see the attributes of a product or the choices of a combo
        """
        setup_product_combo_items(self)
        self.env["product.combo.item"].create({
            "product_id": self.desk_organizer.id,
            "extra_price": 0,
            "combo_id": self.desk_accessories_combo.id,
        })

        for mode in ("mobile", "consultation", "kiosk"):
            self.pos_config.write({"self_ordering_mode": mode})
            # The returned route depend of the pos_config mode
            self_route = self.pos_config._get_self_order_route()
            self.start_tour(self_route, "self_order_pos_closed")

    def test_self_order_config_default_user(self):
        self.pos_config.payment_method_ids = self.pos_config.payment_method_ids.filtered(lambda pm: not pm.is_cash_count)
        for mode in ("mobile", "consultation", "kiosk"):
            self.pos_config.write({"self_ordering_mode": mode})
            with self.assertRaises(UserError):
                self.pos_config.write({"self_ordering_default_user_id": False})
