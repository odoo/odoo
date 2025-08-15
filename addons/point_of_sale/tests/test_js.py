# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo.tests import tagged, HttpCase

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class WebSuite(HttpCase):
    def setUp(self):
        super().setUp()
        env = self.env(user=self.env.ref('base.user_admin'))
        payment_method = env['pos.payment.method'].create({'name': 'Lets Pay for Tests'})
        env['product.product'].create({'name': 'Test Product', 'available_in_pos': True})
        self.main_pos_config = self.main_pos_config = env['pos.config'].create({
            'name': 'Shop',
            'payment_method_ids': [(4, payment_method.id)]
        })

    def test_pos_js(self):
        # open a session, the /pos/ui controller will redirect to it
        self.main_pos_config.open_ui()
        self.main_pos_config.current_session_id.set_cashbox_pos(0, None)

        # point_of_sale desktop test suite
        self.browser_js("/pos/ui/tests?mod=web", "", "", login="admin", timeout=1800)
