# -*- coding: utf-8 -*-
import werkzeug

from odoo import http
from odoo.http import request


class PosSelfKiosk(http.Controller):
    @http.route(["/kiosk/<config_id>", "/kiosk/<config_id>/<path:subpath>"], auth="public", website=True, sitemap=True)
    def pos_self_order_kiosk_start(self, config_id=None, access_token=None):
        pos_config_sudo = request.env["pos.config"].sudo().search([
            ("id", "=", config_id),
            ('access_token', '=', access_token)], limit=1)

        if not access_token or not config_id or not pos_config_sudo:
            raise werkzeug.exceptions.NotFound()

        return request.render(
            'pos_self_order.kiosk_index',
            {
                'session_info': {
                    **request.env["ir.http"].get_frontend_session_info(),
                    'currencies': request.env["ir.http"].get_currencies(),
                    'pos_self_order_data': {
                        'access_token': pos_config_sudo.access_token,
                        **pos_config_sudo._get_self_order_kiosk_data(),
                    },
                }
            }
        )

    @http.route(
        "/kiosk/get-bg-image/<int:pos_config_id>/<type>", methods=["GET"], type="http", auth="public"
    )
    def pos_self_order_get_bg_image(self, pos_config_id, type):
        """
        Gets the background image for this self order
        :return: the bg image
        :rtype: binary
        """
        pos_config_sudo = request.env["pos.config"].sudo().browse(pos_config_id)

        if not pos_config_sudo.self_order_image:
            raise werkzeug.exceptions.NotFound()

        if type == 'eat':
            image_field = 'self_order_kiosk_image_eat'
        elif type == 'home':
            image_field = 'self_order_kiosk_image_home'
        elif type == 'brand':
            image_field = 'self_order_kiosk_image_brand'
        else:
            raise werkzeug.exceptions.NotFound()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(pos_config_sudo, field_name=image_field)
            .get_response()
        )
