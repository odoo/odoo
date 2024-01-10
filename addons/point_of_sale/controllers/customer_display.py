import odoo
from odoo import http
from odoo.http import request
import odoo.exceptions


class PosCustomerDisplay(http.Controller):
    @http.route("/pos_customer_display/<id_>/<access_token>", auth="public", type="http", website=True)
    def pos_customer_display(self, id_, access_token, **kw):
        pos_config_sudo = request.env["pos.config"].sudo().browse(int(id_))
        if not odoo.tools.consteq(access_token, pos_config_sudo.access_token) or pos_config_sudo.customer_display_type == "none":
            raise odoo.exceptions.AccessDenied()
        return request.render(
            "point_of_sale.customer_display_index",
            {
                "session_info": {
                    **request.env["ir.http"].get_frontend_session_info(),
                    **pos_config_sudo._get_customer_display_data(),
                },
            },
        )
