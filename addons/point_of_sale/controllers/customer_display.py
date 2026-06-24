from odoo import http
from odoo.http import request
from odoo.tools import consteq


class PosCustomerDisplay(http.Controller):
    @http.route("/pos_customer_display/<id_>/<device_uuid>", auth="public", type="http", website=True)
    def pos_customer_display(self, id_, device_uuid, **kw):
        pos_config_sudo = request.env["pos.config"].sudo().browse(int(id_))
        if not consteq(kw.get('access_token', ''), pos_config_sudo.access_token):
            return request.not_found()
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
                'theme': kw.get('theme', 'light'),
                "pos_config_id": pos_config_sudo.id,
                "pos_session_id": pos_config_sudo.current_session_id.id if pos_config_sudo.has_active_session else False,
            },
        )
