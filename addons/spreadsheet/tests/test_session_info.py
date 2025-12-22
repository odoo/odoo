# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from uuid import uuid4

from odoo.tests import common


class TestSessionInfo(common.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_password = "password"
        cls.user = common.new_test_user(
            cls.env,
            "user",
            email="user@in.fo",
            password=cls.user_password,
            tz="UTC")

        cls.payload = json.dumps(
            dict(jsonrpc="2.0", method="call", id=str(uuid4())))
        cls.headers = {
            "Content-Type": "application/json",
        }

    def test_session_info(self):
        """
        Checks that the session_info['can_insert_in_spreadsheet'] structure
        correspond to what is expected
        """
        self.authenticate(self.user.login, self.user_password)
        response = self.url_open(
            "/web/session/get_session_info", data=self.payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        session_info = data["result"]

        self.assertEqual(
            session_info["can_insert_in_spreadsheet"],
            False,
            "The session_info['can_insert_in_spreadsheet'] should be False")
