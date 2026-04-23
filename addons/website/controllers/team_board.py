# Part of Odoo. See LICENSE file for full copyright and licensing details.

from gevent import sleep

from odoo import http


class TeamBoardController(http.Controller):
    @http.route(
        "/website/team_board/contact",
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def team_board_contact(self, member_id=None):
        if not member_id:
            return {"success": False, "error": "missing_member_id"}
        sleep(0.8)
        return {"success": True}
