from odoo import http
from odoo.http import request
from odoo.tools import consteq

from ..tools import debug_log as dbg


class PosCustomerDisplay(http.Controller):
    @http.route(
        "/pos_customer_display/<id_>/<device_uuid>",
        auth="public",
        type="http",
        website=True,
    )
    def pos_customer_display(self, id_, device_uuid, access_token=None, **kw):
        try:
            config_id = int(id_)
        except TypeError, ValueError:
            return request.prepare_not_found_error()
        pos_config_sudo = request.env["pos.config"].sudo().browse(config_id).exists()
        if not pos_config_sudo:
            return request.prepare_not_found_error()
        token_ok = bool(access_token) and consteq(
            access_token.encode(), (pos_config_sudo.access_token or "").encode()
        )
        dbg.lifecycle.debug(
            "[http] customer display config=%s device=%s exists=%s active=%s token=%s",
            config_id,
            device_uuid,
            bool(pos_config_sudo),
            pos_config_sudo.has_active_session,
            token_ok,
        )
        if not token_ok or not pos_config_sudo.has_active_session:
            return request.prepare_not_found_error()
        return request.render(
            "point_of_sale.customer_display_index",
            {
                "session_info": {
                    "user_context": {
                        "lang": request.env.user.lang
                        or pos_config_sudo.company_id.partner_id.lang
                    },
                    **request.env["ir.http"].get_frontend_session_info(),
                    **pos_config_sudo._get_customer_display_data(),
                    "device_uuid": device_uuid,
                },
            },
        )
