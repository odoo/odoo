# -*- coding: utf-8 -*-
import werkzeug

from odoo import http
from odoo.http import request


class PosSelfKiosk(http.Controller):
    # The subpath is necessary because the frontend takes care of route management.
    # Sometimes the URL can be: http://localhost:4444/kiosk/5/product/42
    @http.route(["/kiosk/<config_id>", "/kiosk/<config_id>/<path:subpath>"], auth="public", website=True, sitemap=True)
    def pos_self_order_kiosk_start(self, config_id=None, access_token=None):
        if not config_id or not access_token:
            raise werkzeug.exceptions.NotFound()

        pos_config_sudo = request.env["pos.config"].sudo().search([
            ("id", "=", config_id),
            ('access_token', '=', access_token)], limit=1)

        if not pos_config_sudo:
            raise werkzeug.exceptions.NotFound()

        company = pos_config_sudo.company_id
        user = pos_config_sudo.current_session_id.user_id or pos_config_sudo.self_order_default_user_id
        pos_config = pos_config_sudo.sudo(False).with_company(company).with_user(user)

        if not pos_config:
            raise werkzeug.exceptions.NotFound()

        session_info = request.env["ir.http"].get_frontend_session_info()

        return request.render(
            'pos_self_order.kiosk_index',
            {
                'session_info': {
                    **session_info,
                    'currencies': request.env["ir.http"].get_currencies(),
                    'pos_self_order_data': {
                        'access_token': pos_config.access_token,
                        **pos_config._get_self_order_kiosk_data(),
                    },
                }
            }
        )

    @http.route(
        "/kiosk/get-category-image/<int:category_id>",
        methods=["GET"],
        type="http",
        auth="public",
    )
    def pos_self_order_get_image(self, category_id: int):
        category = request.env["pos.category"].sudo().browse(category_id)

        if not category.has_image:
            raise werkzeug.exceptions.NotFound()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(
                category,
                field_name="image_128",
            )
            .get_response()
        )
