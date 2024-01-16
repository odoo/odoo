# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import odoo.addons.web.tests.test_js
import odoo.tests

_logger = logging.getLogger(__name__)


@odoo.tests.tagged("post_install", "-at_install")
class WebSuite(odoo.tests.HttpCase):
    def setUp(self):
        super().setUp()
        env = self.env(user=self.env.ref('base.user_admin'))
        self.main_pos_config = self.main_pos_config = env['pos.config'].create({
            'name': 'Shop',
            'barcode_nomenclature_id': env.ref('barcodes.default_barcode_nomenclature').id,
        })

    def test_pos_js(self):
        # open a session, the /pos/ui controller will redirect to it
        # TODO: Adapt to work without demo data
        if not odoo.tests.loaded_demo_data(self.env):
            _logger.warning("This test relies on demo data. To be rewritten independently of demo data for accurate and reliable results.")
            return

        self.main_pos_config.open_session_cb(check_coa=False)

        # point_of_sale desktop test suite
        self.browser_js(
            "/pos/ui/tests?mod=web&failfast", "", "", login="admin", timeout=1800
        )
