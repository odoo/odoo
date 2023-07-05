# -*- coding: utf-8 -*-

from typing import Optional
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.pos_self_order.controllers.utils import get_any_pos_config_sudo


class PosQRMenuController(http.Controller):
    @http.route(
        [
            "/self-order/get-image/<int:product_id>",
            "/self-order/get-image/<int:product_id>/<int:image_size>",
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
        "/self-order/get-bg-image/<int:pos_config_id>", methods=["GET"], type="http", auth="public"
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
