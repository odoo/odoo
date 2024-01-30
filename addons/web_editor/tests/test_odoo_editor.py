# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


class TestOdooEditor(odoo.tests.HttpCase):

    def test_odoo_editor_suite(self):
        self.browser_js('/web_editor/tests', "", "", login='admin', timeout=1800)
