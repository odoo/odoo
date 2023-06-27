# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUnsplashBeacon(odoo.tests.HttpCase):

    def test_01_beacon(self):
        self.env['ir.config_parameter'].sudo().set_param('unsplash.app_id', '123456')
        # Create page with unsplash image.
        page = self.env['website.page'].search([('url', '=', '/'), ('website_id', '=', 1)])
        page.arch = '''<t name="Homepage" t-name="website.homepage1">
        <t t-call="website.layout">
            <t t-set="pageName" t-value="'homepage'"/>
            <div id="wrap" class="oe_structure oe_empty">
                <img src="/unsplash/pYyOZ8q7AII/306/fairy.jpg"/>
            </div>
            </t>
        </t>'''
        # Access page.
        self.start_tour("/?test_unsplash_beacon", "test_unsplash_beacon")
