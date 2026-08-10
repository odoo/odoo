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

    def test_product_sorting(self):
        """Verify that products are sorted by favorite then by sequence and then by name in self ordering"""
        self.pos_config.write({"self_ordering_mode": "mobile"})
        names = [item["display_name"] for item in self.env["product.template"]._load_pos_self_data_search_read({}, self.pos_config)]
        self.assertEqual(names, ['[12345] Coca-Cola', '[12345] Free', 'Fanta', 'Ketchup', 'Desk Organizer', '[DELIVERY] Delivery Fee (Self-order)', '[FEE] Service Fee'])

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
