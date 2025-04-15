from odoo import http
from odoo.http import request


class PosCustomerDisplay(http.Controller):
    @http.route("/pos_customer_display/<id_>/<device_uuid>", auth="public", type="http", website=True)
    def pos_customer_display(self, id_, device_uuid, **kw):
        pos_config_sudo = request.env["pos.config"].sudo().browse(int(id_))
        return request.render(
            "point_of_sale.customer_display_index",
            {
                "session_info": {
                    "user_context": {
                      "lang":  request.env.user.lang or pos_config_sudo.company_id.partner_id.lang
                    },
                    **request.env["ir.http"].get_frontend_session_info(),
                    **pos_config_sudo._get_customer_display_data(),
                    'device_uuid': device_uuid,
                },
            },
        )
