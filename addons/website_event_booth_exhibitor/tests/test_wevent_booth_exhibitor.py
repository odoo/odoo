# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestWEventBoothExhibitorCommon(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def test_register(self):
        self.browser_js(
            '/event',
            'odoo.__DEBUG__.services["web_tour.tour"].run("webooth_exhibitor_register")',
            'odoo.__DEBUG__.services["web_tour.tour"].tours.webooth_exhibitor_register.ready',
            login='admin'
        )
