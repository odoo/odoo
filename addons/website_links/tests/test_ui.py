# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def test_01_test_ui(self):
        self.env['link.tracker'].create({
            'campaign_id': 2,
            'medium_id': 2,
            'source_id': 2,
            'url': self.env["ir.config_parameter"].sudo().get_param("web.base.url") + '/contactus',
        })
        self.start_tour("/", 'website_links_tour', login="admin")
