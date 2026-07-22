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
            },
        )

    @http.route("/pos_customer_display/<int:id_>/<device_uuid>/alive", auth="public", type="jsonrpc")
    def pos_customer_display_alive(self, id_, device_uuid, access_token='', needs_data=False):
        """ Let the PoS know a customer display is listening, so that it only
        pushes updates to the bus while one is actually open. ``needs_data``
        tells it the display has nothing to show yet and must be given the
        current order right away. """
        pos_config_sudo = request.env["pos.config"].sudo().browse(id_)
        if not access_token or not consteq(access_token, pos_config_sudo.access_token or ''):
            raise request.not_found()
        pos_config_sudo._notify("CUSTOMER_DISPLAY_ALIVE", {
            "device_uuid": device_uuid,
            "needs_data": bool(needs_data),
        })
