# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestTeamBoardController(HttpCase):
    def test_team_board_page(self):
        response = self.url_open("/team-board")

        response.raise_for_status()
        self.assertIn(b"Team Board", response.content)
        self.assertIn(b"s_team_board", response.content)

    def test_team_board_contact_requires_member_id(self):
        result = self.make_jsonrpc_request("/website/team_board/contact", {})

        self.assertEqual(result, {"success": False, "error": "missing_member_id"})

    def test_team_board_contact_succeeds_with_member_id(self):
        with patch("odoo.addons.website.controllers.team_board.sleep") as sleep_mock:
            result = self.make_jsonrpc_request(
                "/website/team_board/contact",
                {"member_id": "member_1"},
            )

        self.assertEqual(result, {"success": True})
        sleep_mock.assert_called_once_with(0.8)
