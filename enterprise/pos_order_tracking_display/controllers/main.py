# -*- coding: utf-8 -*-

import werkzeug

from odoo import http
from odoo.http import request


class PosOrderTrackingDisplay(http.Controller):
    @http.route("/pos-order-tracking/", auth="public", type="http", website=True)
    def pos_order_tracking_display(self, access_token):
        preparation_display_sudo = (
            request.env["pos_preparation_display.display"]
            .sudo()
            .search([("access_token", "=", access_token)], limit=1)
        )
        if not preparation_display_sudo:
            raise werkzeug.exceptions.NotFound()
        return request.render(
            "pos_order_tracking_display.index",
            {
                "session_info": {
                    **request.env["ir.http"].get_frontend_session_info(),
                    "preparation_display": preparation_display_sudo.read(["access_token"])[0],
                    "initial_data": preparation_display_sudo._get_pos_orders(),
                    "db": request.env.cr.dbname,
                },
            },
        )
