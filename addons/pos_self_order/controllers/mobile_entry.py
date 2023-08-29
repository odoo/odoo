# -*- coding: utf-8 -*-

from typing import Optional
import werkzeug

from odoo import http
from odoo.http import request

from odoo.addons.pos_self_order.controllers.utils import (
    get_any_pos_config_sudo,
    reduce_privilege,
)


class PosQRMenuController(http.Controller):
    """
    This is the controller for the POS Self Order App
    There is one main route that the client will use to access the POS Self Order App: /menu
    This route will render the LANDING PAGE of the POS Self Order App
    And it will pass the needed data to the template: the list of products, pos_config_id, table_id, company_name, currency...
    After that the client will be able to navigate to the /products route w/o additional requests
    to the server, using client side routing.
    """

    @http.route(
            [
                "/menu/",
                "/menu/<config_id>",
                "/menu/<config_id>/<path:subpath>"
            ],
        auth="public", website=True, sitemap=True,
    )
    def pos_self_order_start(self, config_id=None, access_token=None, table_identifier=None):
        self_order_mode = 'qr_code'
        pos_config_sudo = False
        table_sudo = False
        config_access_token = False

        if config_id and config_id.isnumeric() and access_token:
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id),
                ('access_token', '=', access_token)], limit=1)

            if pos_config_sudo:
                config_access_token = pos_config_sudo.access_token
            else:
                raise werkzeug.exceptions.Unauthorized()

        if pos_config_sudo and pos_config_sudo.has_active_session and pos_config_sudo.self_order_table_mode:
            self_order_mode = pos_config_sudo.self_order_pay_after
            table_sudo = table_identifier and (
                request.env["restaurant.table"]
                .sudo()
                .search([("identifier", "=", table_identifier), ("active", "=", True)], limit=1)
            )
        elif config_id and config_id.isnumeric():
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ("self_order_view_mode", "=", True)], limit=1)
        else:
            pos_config_sudo = get_any_pos_config_sudo()

        company = pos_config_sudo.company_id
        user = pos_config_sudo.current_session_id.user_id
        pos_config = reduce_privilege(pos_config_sudo, company, user)
        table = reduce_privilege(table_sudo, company, user)

        if not pos_config:
            raise werkzeug.exceptions.NotFound()

        return request.render(
            'pos_self_order.mobile_index',
            {
                'session_info': {
                    **request.env["ir.http"].get_frontend_session_info(),
                    'currencies': request.env["ir.http"].get_currencies(),
                    'pos_self_order_data': {
                        'self_order_mode': self_order_mode,
                        'table': table._get_self_order_data() if table else False,
                        'access_token': config_access_token,
                        **pos_config._get_self_order_mobile_data(),
                    },
                    "base_url": request.env['pos.session'].get_base_url(),
                }
            }
        )

    @http.route(
        [
            "/menu/get-image/<int:product_id>",
            "/menu/get-image/<int:product_id>/<int:image_size>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def pos_self_order_get_image(self, product_id, image_size=128, **kw):
        # This controller is public and does not require an access code (access_token) because the user
        # needs to see the product image in "menu" mode. In this mode, the user has no access_token.
        if not get_any_pos_config_sudo():
            raise werkzeug.exceptions.Unauthorized()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(
                request.env["product.product"].sudo().browse(product_id),
                field_name=f"image_{image_size}",
            )
            .get_response()
        )
