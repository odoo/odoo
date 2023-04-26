# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class TestFrontend(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "Bar",
                "module_pos_restaurant": True,
                "iface_splitbill": True,
                "iface_printbill": True,
                "iface_orderline_notes": True,
                "start_category": True,
                "self_order_view_mode": True,
            }
        )
        basic_product = {
            "name": "Test Product",
            "type": "product",
            "available_in_pos": True,
            "list_price": 10,
            "taxes_id": False,
        }
        self.env["product.product"].create([basic_product for i in range(1000)])

    def test_self_order_tour(self):
        self.start_tour(
            f"/menu/{self.pos_config.id}",
            "pos_self_order_tour",
            login=None,
        )
