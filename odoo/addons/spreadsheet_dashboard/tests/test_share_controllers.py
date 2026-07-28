import json
import base64

from odoo.tests.common import HttpCase
from odoo.tools import mute_logger

from .common import DashboardTestCommon

class TestShareController(DashboardTestCommon, HttpCase):
    def test_dashboard_share_portal(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        response = self.url_open(f"/dashboard/share/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_share_portal_wrong_token(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        with mute_logger('odoo.http'):
            response = self.url_open(f"/dashboard/share/{share.id}/a-random-token")
        self.assertEqual(response.status_code, 403)

    def test_public_dashboard_data(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        response = self.url_open(f"/dashboard/data/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), json.loads(dashboard.spreadsheet_data))

    def test_public_dashboard_data_wrong_token(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/dashboard/data/{share.id}/a-random-token")
        self.assertEqual(response.status_code, 403)

    def test_public_dashboard_revoked_access(self):
        dashboard = self.create_dashboard()
        with self.with_user(self.user.login):
            share = self.share_dashboard(dashboard)

        response = self.url_open(f"/dashboard/data/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200) # access granted

        self.user.groups_id -= self.group # revoke access

        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/dashboard/data/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 403)

    def test_download_dashboard(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        share.excel_export = base64.b64encode(b"test")
        response = self.url_open(f"/dashboard/download/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"test")

    def test_download_dashboard_wrong_token(self):
        dashboard = self.create_dashboard()
        share = self.share_dashboard(dashboard)
        share.excel_export = base64.b64encode(b"test")
        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/dashboard/download/{share.id}/a-random-token")
        self.assertEqual(response.status_code, 403)

    def test_download_dashboard_revoked_access(self):
        dashboard = self.create_dashboard()
        with self.with_user(self.user.login):
            share = self.share_dashboard(dashboard)
        share.excel_export = base64.b64encode(b"test")
        response = self.url_open(f"/dashboard/download/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 200) # access granted

        self.user.groups_id -= self.group # revoke access

        with mute_logger('odoo.http'):  # mute 403 warning
            response = self.url_open(f"/dashboard/download/{share.id}/{share.access_token}")
        self.assertEqual(response.status_code, 403)
