import random
import time

from odoo import http


class WebsiteBackend(http.Controller):
    @http.route(
        "/website/team_board_contact",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def fetch_dashboard_data(self):
        time.sleep(1)
        return {'ok': random.random() < 0.5}
