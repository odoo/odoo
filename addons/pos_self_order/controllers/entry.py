# -*- coding: utf-8 -*-

from typing import Optional
import werkzeug

from odoo import http
from odoo.http import request

from odoo.addons.pos_self_order.controllers.utils import (
    get_any_pos_config_sudo,
    get_table_sudo,
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
        table_infos = False
        pos_config_sudo = False
        pos_config_access_token = False

        if config_id and config_id.isnumeric() and access_token:
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id),
                ('access_token', '=', access_token)], limit=1)

        if pos_config_sudo and pos_config_sudo.has_active_session and pos_config_sudo.self_order_table_mode:
            self_order_mode = pos_config_sudo.self_order_pay_after
            pos_config_access_token = pos_config_sudo.access_token
            table_sudo = get_table_sudo(identifier=table_identifier)
            table_infos = table_sudo._get_self_order_data() if table_sudo else False
        elif config_id and config_id.isnumeric():
            pos_config_sudo = request.env["pos.config"].sudo().search([
                ("id", "=", config_id), ("self_order_view_mode", "=", True)], limit=1)
        else:
            pos_config_sudo = get_any_pos_config_sudo()

        if not pos_config_sudo:
            raise werkzeug.exceptions.NotFound()

        return request.render(
            'pos_self_order.index',
            {
                'session_info': {
                    **request.env["ir.http"].get_frontend_session_info(),
                    'currencies': request.env["ir.http"].get_currencies(),
                    'pos_self_order_data': {
                        'self_order_mode': self_order_mode,
                        'table': table_infos,
                        'access_token': pos_config_access_token,
                        **pos_config_sudo._get_self_order_data(),
                    },
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
    def pos_self_order_get_image(self, product_id: int, image_size: Optional[int] = 128):
        """
        This is the route that the POS Self Order App uses to GET THE PRODUCT IMAGES.
        :return: the image of the product (or a default one in case no product is found)
            or an exception if there is no pos configured as self order.
        :rtype: binary
        """
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

    @http.route(
        "/menu/get-bg-image/<int:pos_config_id>", methods=["GET"], type="http", auth="public"
    )
    def pos_self_order_get_bg_image(self, pos_config_id: int):
        """
        Gets the background image for this self order
        :return: the bg image
        :rtype: binary
        """
        pos_config_sudo = request.env["pos.config"].sudo().browse(pos_config_id)

        if not pos_config_sudo.self_order_image:
            raise werkzeug.exceptions.NotFound()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(pos_config_sudo, field_name="self_order_image")
            .get_response()
        )
