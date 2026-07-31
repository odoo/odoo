from odoo import http
from odoo.http import request


class OwlybookController(http.Controller):
    @http.route(["/pos_owlybook"], type="http", auth="user")
    def show_owlybook(self):
        return request.render(
            "pos_owlybook.owlybook",
            {
                "session_info": request.env["ir.http"].session_info(),
            },
        )
