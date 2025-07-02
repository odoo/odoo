# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.common_setup_methods import setup_product_combo_items
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest

from odoo.exceptions import UserError


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderCommon(SelfOrderCommonTest):
    def test_self_order_common(self):
        self.pos_config.write({
            'self_ordering_default_user_id': self.pos_admin.id,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'available_preset_ids': [(5, 0)],
        })

        self.pos_admin.group_ids += self.env.ref('account.group_account_invoice')
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

    def test_self_order_pos_landing_page_carousel(self):
        for mode in ("mobile", "consultation", "kiosk"):
            self.pos_config.write({"self_ordering_mode": mode})
            self.start_tour(self.pos_config._get_self_order_route(), "self_order_landing_page_carousel")

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

        for mode in ("mobile", "consultation"):
            self.pos_config.write({"self_ordering_mode": mode})
            # The returned route depend of the pos_config mode
            self_route = self.pos_config._get_self_order_route()
            self.start_tour(self_route, "self_order_pos_closed")

        # Kiosk test
        self.pos_config.write({"self_ordering_mode": "kiosk"})
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "kiosk_order_pos_closed")

    def test_self_order_config_default_user(self):
        self.pos_config.payment_method_ids = self.pos_config.payment_method_ids.filtered(lambda pm: not pm.is_cash_count)
        for mode in ("mobile", "consultation", "kiosk"):
            self.pos_config.write({"self_ordering_mode": mode})
            with self.assertRaises(UserError):
                self.pos_config.write({"self_ordering_default_user_id": False})

    def test_product_self_order_visible(self):
        """
        Test that the self_order_visible field is correctly computed and stored
        for products based on their categories and self_ordering_mode.
        """
        pos_category = self.env['pos.category'].create({
            'name': 'Test Category',
        })
        another_pos_category = self.env['pos.category'].create({
            'name': 'Another Category',
        })
        product = self.env['product.template'].create({
            'name': 'Test Product',
            'list_price': 10.0,
            'available_in_pos': True,
            'pos_categ_ids': [(6, 0, [pos_category.id])],
        })

        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'iface_available_categ_ids': [(6, 0, [pos_category.id])],
            'limit_categories': True,
        })

        self.assertTrue(product.self_order_visible, "the field should be visible when the pos config is set to kiosk and the category is available")

        self.pos_config.write({
            'iface_available_categ_ids': [(6, 0, [another_pos_category.id])],
        })

        self.assertFalse(product.self_order_visible, "the field should not be visible when the category is not available in the pos config")

        self.pos_config.write({
            'iface_available_categ_ids': [(4, pos_category.id)],
        })

        self.assertTrue(product.self_order_visible, "the field should be visible again when the category is added back to the pos config")

        self.pos_config.write({
            'self_ordering_mode': 'nothing',
        })

        self.assertFalse(product.self_order_visible, "the field should not be visible when the pos config is set to 'nothing'")

        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
        })

        self.assertTrue(product.self_order_visible, "the field should be visible again when the pos config is set to 'kiosk'")

        self.pos_config.write({
            'iface_available_categ_ids': [(3, pos_category.id)],
        })

        self.assertFalse(product.self_order_visible, "the field should not be visible when the pos config has no available categories")

        self.pos_config.write({
            'limit_categories': False,
        })

        self.assertTrue(product.self_order_visible, "the field should be visible when the pos config has no limit categories")
