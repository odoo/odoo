# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestSnippet(odoo.tests.HttpCase):
    def test_01_twitter_scroller_reload_button(self):
        self.start_tour("/", "twitter_scroller_reload_button", login='admin')
