# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.tagged("post_install", "-at_install")
class SelfOrderCommonTest(odoo.tests.HttpCase):
    browser_size = "375x667"
    touch_enabled = True

    def setUp(self):
        super().setUp()
        self.pos_config = self.env["pos.config"].create(
            {
                "name": "BarTest",
                "module_pos_restaurant": True,
                "self_order_view_mode": True,
                "floor_ids": self.env["restaurant.floor"].search([]),
                "self_order_table_mode": False,
            }
        )

        # we need a default tax fixed at 15% to all product because in the test prices are based on this tax.
        # some time with the localization this may not be the case. So we force it.
        self.env['product.product'].search([]).taxes_id = self.env['account.tax'].create({
            'name': 'Default Tax for Self Order',
            'amount': 15,
            'amount_type': 'percent',
        })
