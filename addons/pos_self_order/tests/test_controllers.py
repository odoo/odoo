# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.tests import HttpCase

@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderControllers(HttpCase):
    def test_menu_redirect(self):
        response = self.url_open("/menu")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.history[0].status_code, 303)
        chosen_pos_config_id = int(response.url.split("/")[-1])
        available_pos_config_ids = (
            self.env["pos.config"].search([("self_order_view_mode", "=", True)]).ids
        )
        self.assertTrue(chosen_pos_config_id in available_pos_config_ids)

        self.env["pos.config"].search([]).write({"self_order_view_mode": False})
        response = self.url_open("/menu")
        self.assertEqual(response.status_code, 404)
