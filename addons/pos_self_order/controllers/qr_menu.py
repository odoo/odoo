# -*- coding: utf-8 -*-

from typing import Dict, Optional
import werkzeug

from odoo import http
from odoo.http import request

from odoo.addons.pos_self_order.controllers.utils import (
    _raise,
    _get_pos_config_sudo,
    _get_any_pos_config_sudo,
    _get_table_sudo,
)
from odoo.addons.pos_self_order.models.pos_config import PosConfig
from odoo.addons.pos_self_order.models.pos_restaurant import RestaurantTable


"""
TODO:
test custom links name, url , color,  order, pos id restriction
test pos restrict categ
test pos categs orderer
"""


class PosQRMenuController(http.Controller):
    """
    This is the controller for the POS Self Order App
    There is one main route that the client will use to access the POS Self Order App: /menu
    This route will render the LANDING PAGE of the POS Self Order App
    And it will pass the needed data to the template: the list of products, pos_config_id, table_id, company_name, currency...
    After that the client will be able to navigate to the /products route w/o aditional requests
    to the server, using client side routing.
    """

    @http.route("/menu", auth="public")
    def pos_self_order_redirect(self):
        return request.redirect(f"/menu/{_get_any_pos_config_sudo().id}")

    @http.route(
        [
            "/menu/<pos_name>",
            "/menu/<pos_name>/products",
            "/menu/<pos_name>/products/<int:product_id>",
            "/menu/<pos_name>/cart",
            "/menu/<pos_name>/orders",
        ],
        auth="public",
        website=True,
        sitemap=True,
    )
    def pos_self_order_start(
        self, pos_name: str, id: Optional[str] = None, product_id: Optional[int] = None
    ):
        """
        The user gets this route from the QR code that they scan at the table
        :param pos_name: the name of the pos config: can be the id or the slugified name of the pos config. (e.g. "3" or "bar-3")
        :param id: the access token of the table; we call this argument "id" because
            it will be displayed in the url ( as a query param ), and "id" is more user friendly than "table_access_token"
            the user is allowed to order only if this "id" matches the access token of a table
        :param product_id: the id of the product that the user wants to see the details of;
            we never actually use this argument in this function ( it will be read by the client side router ),
            but we still have it here, because otherwise we get a Warning in the logs
        :return: the rendered template
        """
        return request.render(
            "pos_self_order.index",
            {
                "session_info": {
                    **request.env["ir.http"].get_frontend_session_info(),
                    "currencies": request.env["ir.http"].get_currencies(),
                    "pos_self_order": self._get_self_order_config(
                        _get_pos_config_sudo(pos_name),
                        _get_table_sudo(table_access_token=id),
                    ),
                }
            },
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
        if not _get_any_pos_config_sudo():
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
        pos_config_sudo = _get_pos_config_sudo(pos_config_id)

        if not pos_config_sudo.self_order_image:
            raise werkzeug.exceptions.NotFound()

        return (
            request.env["ir.binary"]
            ._get_image_stream_from(pos_config_sudo, field_name="self_order_image")
            .get_response()
        )

    def _get_self_order_config(
        self, pos_config_sudo: PosConfig, table_sudo: RestaurantTable
    ) -> Dict:
        """
        Returns the necessary information for the POS Self Order App
        """
        return {
            **pos_config_sudo._get_self_order_data(),
            **(
                table_sudo
                and pos_config_sudo.has_active_session
                and pos_config_sudo.self_order_table_mode
                # having the table_id in the frontend means that the client will be able to order
                and {"table": table_sudo._get_self_order_data()}
                or {}
            ),
        }
