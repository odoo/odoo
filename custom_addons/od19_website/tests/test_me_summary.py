import datetime

from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestMeSummary(HttpCase):
    def setUp(self):
        super().setUp()
        self.tester = self.env["res.users"].create(
            {
                "name": "Emp Exp Tester",
                "login": "emp_exp_tester",
                "password": "emp_exp_tester",
                "group_ids": [Command.link(self.env.ref("base.group_user").id)],
            }
        )

    def test_me_summary_returns_json_with_expected_keys(self):
        self.authenticate("emp_exp_tester", "emp_exp_tester")
        response = self.url_open("/employee-portal/me-summary")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        for key in (
            "attendance",
            "approvals",
            "next_booking",
            "leave",
            "unread_announcements",
            "schedule",
        ):
            self.assertIn(key, payload)
        self.assertIn("available", payload["attendance"])
        self.assertIn("pending_count", payload["approvals"])
        self.assertIsInstance(payload["schedule"], list)

    def test_me_summary_requires_login(self):
        response = self.url_open("/employee-portal/me-summary", allow_redirects=False)
        self.assertIn(response.status_code, (302, 303, 401, 403))
