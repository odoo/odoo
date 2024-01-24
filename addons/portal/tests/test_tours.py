# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserPortal):
    def test_01_portal_load_tour(self):
        self.start_tour("/", 'portal_load_homepage', login="portal")

    def test_02_portal_load_tour_cant_edit_vat(self):
        willis = self.env.ref('base.demo_user0')
        willis.parent_id = self.env.ref('base.partner_demo').id
        self.start_tour("/", 'portal_load_homepage', login="portal")
        self.assertEqual(willis.phone, "+1 555 666 7788")
