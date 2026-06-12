# Part of Odoo. See LICENSE file for full copyright and licensing details.

from gevent import sleep

from odoo import http
from odoo.http import request


class TeamBoardController(http.Controller):
    @http.route(
        "/team-board",
        type="http",
        auth="public",
        website=True,
        sitemap=True,
        readonly=True,
    )
    def team_board_page(self):
        return request.render("website.team_board_page")

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
