# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import DashboardTestCommon
from odoo.exceptions import AccessError

EXCEL_FILES = [
    {
        "content": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "path": "[Content_Types].xml",
    }
]

class DashboardSharing(DashboardTestCommon):
    def test_share_url(self):
        dashboard = self.create_dashboard()
        share_vals = {
            "spreadsheet_data": dashboard.spreadsheet_data,
            "dashboard_id": dashboard.id,
            "excel_files": EXCEL_FILES,
        }
        url = self.env["spreadsheet.dashboard.share"].action_get_share_url(share_vals)
        share = self.env["spreadsheet.dashboard.share"].search(
            [("dashboard_id", "=", dashboard.id)]
        )
        self.assertEqual(url, share.full_url)
        self.assertEqual(share.dashboard_id, dashboard)
        self.assertTrue(share.excel_export)

    def test_can_create_own(self):
        dashboard = self.create_dashboard()
        with self.with_user(self.user.login):
            share = self.share_dashboard(dashboard)

        self.assertTrue(share)
        self.assertTrue(share.create_uid, self.user)

    def test_cannot_read_others(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        with self.assertRaises(AccessError):
            share.with_user(self.user).access_token
