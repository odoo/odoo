# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # be sure some expected values are set otherwise homepage may fail
        cls.partner_portal.write({
            "city": "Bayonne",
            "company_name": "YourCompany",
            "country_id": cls.env.ref("base.us").id,
            "phone": "(683)-556-5104",
            "street": "858 Lynn Street",
            "zip": "07002",
        })

    def test_01_portal_load_tour(self):
        self.start_tour("/", 'portal_load_homepage', login="portal")

    def test_02_portal_load_tour_cant_edit_vat(self):
        willis = self.user_portal
        willis.parent_id = self.user_demo.partner_id.id
        self.start_tour("/", 'portal_load_homepage_forbidden', login="portal")
        self.assertNotEqual(willis.phone, "+1 555 666 7788")

    def test_03_skip_to_content(self):
        self.start_tour("/", "skip_to_content", login="portal")
