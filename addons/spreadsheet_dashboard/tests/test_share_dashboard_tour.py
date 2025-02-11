# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import DashboardTestCommon

from odoo.tests import tagged
from odoo.tests.common import HttpCase

@tagged("post_install", "-at_install")
class TestDashboardShareTour(DashboardTestCommon, HttpCase):
    def test_open_public_dashboard(self):
        """check the public spreadsheet page can be opened without error"""
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        # web_tour is not part of the public dashboard assets bundle.
        # We can't use the start_tour helper method.
        self.browser_js(
            "/dashboard/share/%s/%s" % (share.id, share.access_token),
            "console.log('test successful');",
            ready="odoo.isReady",
        )
