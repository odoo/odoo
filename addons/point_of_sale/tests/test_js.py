# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, HttpCase


@tagged("post_install", "-at_install")
class WebSuite(HttpCase):
    def setUp(self):
        super().setUp()
        env = self.env(user=self.env.ref('base.user_admin'))
        self.main_pos_config = env.ref('point_of_sale.pos_config_main')

    def test_pos_js(self):
        import unittest; raise unittest.SkipTest("skipWOWL")
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.open_session_cb()
        self.main_pos_config.current_session_id.set_cashbox_pos(0, None)

        # point_of_sale desktop test suite
        self.browser_js("/pos/ui/tests?mod=web", "", "", login="admin", timeout=1800)
