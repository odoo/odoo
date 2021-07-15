# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def setUp(self):
        super(TestUi, self).setUp()

        def _get_title_from_url(addr, **kw):
            return 'Contact Us | My Website'

        patcher = patch('odoo.addons.link_tracker.models.link_tracker.LinkTracker._get_title_from_url', wraps=_get_title_from_url)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_01_test_ui(self):
        self.env['link.tracker'].create({
            'campaign_id': 2,
            'medium_id': 2,
            'source_id': 2,
            'url': self.env["ir.config_parameter"].sudo().get_param("web.base.url") + '/contactus',
        })
        self.start_tour("/", 'website_links_tour', login="admin")
