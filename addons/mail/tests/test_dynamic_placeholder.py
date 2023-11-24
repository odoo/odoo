# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import tagged
from odoo.addons.base.tests.common import HttpCaseWithUserDemo


@tagged("-at_install", "post_install")
class TestDynamicPlaceholder(HttpCaseWithUserDemo):

    def test_email_template_dph_tour(self):
        self.start_tour("/web", 'dynamic_placeholder_tour', login="admin")
