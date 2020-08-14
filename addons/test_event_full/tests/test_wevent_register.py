# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.addons.test_event_full.tests.common import TestWEventCommon
from odoo.tests.common import HOST


@tests.common.tagged('post_install', '-at_install')
class TestWEventRegister(TestWEventCommon):

    def test_register(self):
        self.browser_js(
            '/event',
            'odoo.__DEBUG__.services["web_tour.tour"].run("wevent_register")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.wevent_register.ready',
            login=None
        )
