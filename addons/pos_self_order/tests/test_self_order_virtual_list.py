# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderVirtualList(SelfOrderCommonTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Categories
        createCategories = [{"name": f"C{i}"} for i in range(0, 11)]
        pos_categories = cls.env["pos.category"].create(createCategories)

        # Subcategories
        createSubcategories = [
            {
                "name": f"C{c}.{i}",
                "parent_id": pos_categories[c].id,
            }
            for i in range(0, 3)
            for c in range(0, 10)
        ]
        cls.env["pos.category"].create(createSubcategories)

        # Products
        createProducts = []
        for c in range(0, 10):  # Categories
            for i in range(0, 6):  # Products
                pos_categ_ids = [(4, pos_categories[c].id)]

                # Add subcategory only if i % 4 != 3
                if i % 4 != 3:
                    sub = cls.env["pos.category"].search(
                        [
                            ("parent_id", "=", pos_categories[c].id),
                            ("name", "=", f"C{c}.{i % 4}"),
                        ],
                        limit=1,
                    )
                    if sub:
                        pos_categ_ids.append((4, sub.id))

                createProducts.append(
                    {
                        "name": f"C{c}-P{i}",
                        "is_storable": True,
                        "list_price": 10 + i,
                        "taxes_id": False,
                        "available_in_pos": True,
                        "pos_categ_ids": pos_categ_ids,
                        "default_code": f"--{c}.{i}--",
                    },
                )

        cls.env["product.product"].create(createProducts)

    def test_self_order_virtual_consultation(self):
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "test_self_order_virtual_consultation")

    def test_self_order_virtual_kiosk(self):
        self.pos_config.write({"self_ordering_mode": "kiosk"})

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()

        self.start_tour(self_route, "test_self_order_virtual_kiosk")
