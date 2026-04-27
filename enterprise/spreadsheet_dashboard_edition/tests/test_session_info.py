# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from uuid import uuid4

from odoo.tests import common


class TestSessionInfo(common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_password = "password"
        cls.user1 = common.new_test_user(
            cls.env,
            "user1",
            email="user1@in.fo",
            password=cls.user_password,
            tz="UTC")

        cls.user2 = common.new_test_user(
            cls.env,
            "user2",
            email="user2@in.fo",
            password=cls.user_password,
            tz="UTC",
            groups="spreadsheet_dashboard.group_dashboard_manager")

        cls.headers = {
            "Content-Type": "application/json",
        }

    def _payload(self):
        """
        Helper to properly build jsonrpc payload
        """
        return json.dumps({
            "jsonrpc": "2.0",
            "method": "call",
            "id": str(uuid4()),
        })

    def test_session_info_without_right(self):
        """
        Checks that the session_info['can_insert_in_spreadsheet'] structure
        correspond to what is expected
        """
        self.authenticate(self.user1.login, self.user_password)
        response = self.url_open(
            "/web/session/get_session_info", data=self._payload(), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        session_info = data["result"]

        self.assertEqual(
            session_info["can_insert_in_spreadsheet"],
            False,
            "The session_info['can_insert_in_spreadsheet'] should be False")

    def test_session_info_with_right(self):
        """
        Checks that the session_info['can_insert_in_spreadsheet'] structure
        correspond to what is expected
        """
        self.authenticate(self.user2.login, self.user_password)
        response = self.url_open(
            "/web/session/get_session_info", data=self._payload(), headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        session_info = data["result"]

        self.assertEqual(
            session_info["can_insert_in_spreadsheet"],
            True,
            "The session_info['can_insert_in_spreadsheet'] should be True")
