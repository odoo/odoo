# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserPortal):
    def test_01_portal_load_tour(self):
        self.start_tour("/", 'portal_load_homepage', login="portal")
