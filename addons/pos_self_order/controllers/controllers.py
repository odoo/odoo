# -*- coding: utf-8 -*-

from typing import List, Dict, Optional
import werkzeug

from odoo import http
from odoo.http import request

from odoo.addons.http_routing.models.ir_http import unslug
from odoo.addons.point_of_sale.models.product import ProductProduct
from odoo.addons.pos_self_order.models.pos_config import PosConfig


class PosSelfOrderController(http.Controller):
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
        pos_config_id = self._get_any_pos_config_with_qr_code_menu_sudo().id
        return request.redirect(f"/menu/{pos_config_id}")

    @http.route(
        [
            "/menu/<pos_name>",
            "/menu/<pos_name>/products",
            "/menu/<pos_name>/products/<int:product_id>",
        ],
        auth="public",
        website=True,
        sitemap=True
    )
    def pos_self_order_start(self, pos_name: str):
        """
        The user gets this route from the QR code that they scan at the table
        :param pos_name: the name of the pos config: can be the id or the slugified name of the pos config
        :return: the rendered template
        """
        _, pos_config_id = unslug(pos_name)
        if not pos_config_id:
            raise werkzeug.exceptions.NotFound()
        pos_config_sudo = self._get_pos_config_sudo(pos_config_id)
        session_info = request.env["ir.http"].get_frontend_session_info()
        session_info.update({
            "currencies": request.env["ir.http"].get_currencies(),
            "pos_self_order": self._get_self_order_config(pos_config_sudo),
        })
        response = request.render("pos_self_order.index", {"session_info": session_info})
        return response

    @http.route(
        [
            "/menu/get-image/<int:product_id>",
            "/menu/get-image/<int:product_id>/<int:image_size>",
        ],
        methods=["GET"],
        type="http",
        auth="public",
    )
    def pos_self_order_get_image(self, product_id: int, image_size: Optional[int] = None):
        """
        This is the route that the POS Self Order App uses to GET THE PRODUCT IMAGES
        :return: the image of the product
        :rtype: binary
        """,
        # The idea here is to not show the image if there is no pos with the self order menu
        if not self._get_any_pos_config_with_qr_code_menu_sudo():
            raise werkzeug.exceptions.NotFound()

        product_sudo = request.env["product.product"].sudo().browse(product_id)
        if not product_sudo.available_in_pos:
            raise werkzeug.exceptions.NotFound()

        if image_size == 1920 and product_sudo.image_1920:
            return (
                request.env["ir.binary"]
                ._get_image_stream_from(product_sudo, field_name="image_1920")
                .get_response()
            )
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(product_sudo, field_name="image_128")
            .get_response()
        )

    @http.route("/menu/get-bg-image", methods=["GET"], type="http", auth="public")
    def pos_self_order_get_bg_image(self, pos_config_id: int):
        """
        Gets the background image for this self order
        :return: the bg image
        :rtype: binary
        """,
        pos_config_sudo = self._get_pos_config_sudo(pos_config_id)
        if not pos_config_sudo.self_order_image:
            raise werkzeug.exceptions.NotFound()
        return (
            request.env["ir.binary"]
            ._get_image_stream_from(pos_config_sudo, field_name="self_order_image")
            .get_response()
        )

    def _get_any_pos_config_with_qr_code_menu_sudo(self) -> PosConfig:
        """
        Returns a PosConfig that allows the QR code menu, if there is one,
        or raises a NotFound otherwise
        """
        pos_config_sudo = (
            request.env["pos.config"]
            .sudo()
            .search([("self_order_view_mode", "=", True)], limit=1)
        )
        if not pos_config_sudo:
            raise werkzeug.exceptions.NotFound()
        return pos_config_sudo

    def _get_pos_config_sudo(self, pos_config_id: int) -> PosConfig:
        """
        Returns the PosConfig if pos_config_id exist and the pos is configured to allow the menu to be viewed online.
        If not, it raises a NotFound
        """
        pos_config_sudo = request.env["pos.config"].sudo().browse(
            int(pos_config_id))
        if not pos_config_sudo or not pos_config_sudo.self_order_view_mode:
            raise werkzeug.exceptions.NotFound()
        return pos_config_sudo

    def _get_self_order_config(self, pos_config_sudo: PosConfig) -> Dict:
        """
        Returns the necessary information for the POS Self Order App
        """
        return {
            "pos_config_id": pos_config_sudo.id,
            "company_name": pos_config_sudo.company_id.name,
            "currency_id": pos_config_sudo.currency_id.id,
            "show_prices_with_tax_included": pos_config_sudo.iface_tax_included == "total",
            "custom_links": self._get_custom_links(pos_config_sudo.id),
            "attributes_by_ptal_id": request.env["pos.session"].sudo()._get_attributes_by_ptal_id(),
            "products": self._get_data_from_products(self._get_available_products_sudo(pos_config_sudo.id), pos_config_sudo.id),
        }

    def _get_custom_links(self, pos_config_id: int) -> List[Dict[str, str]]:
        """
        On the landing page of the app we can have a number of custom links
        that are defined by the restaurant employee in the backend.
        This function returns a list of dictionaries with the attributes of each link
        that is available for the POS with id pos_config_id.
        """
        domain = [
            "|",
            ("pos_config_ids", "in", [pos_config_id]),
            ("pos_config_ids", "=", False),
        ]
        return (
            request.env["pos_self_order.custom_link"]
            .sudo()
            .search_read(domain, fields=["name", "url", "style"], order="sequence")
        )

    def _get_available_products_sudo(self, pos_config_id: int) -> ProductProduct:
        """
        This function returns the products that are available in the POS with id pos_config_id
        """
        domain = [("available_in_pos", "=", True)]
        pos_config_sudo = self._get_pos_config_sudo(pos_config_id)
        if (pos_config_sudo.limit_categories and pos_config_sudo.iface_available_categ_ids):
            domain.append(("pos_categ_id", "in", pos_config_sudo.iface_available_categ_ids.ids))
        return (
            request.env["product.product"]
            .sudo()
            .search(domain, order="pos_categ_id.sequence asc nulls last")
        )

    def _get_data_from_products(self, products_sudo: ProductProduct, pos_config_id: int) -> List[Dict[str, str]]:
        """
        This function adds the price info to each product in the list products_sudo
        and returns the list of products with the necessary info
        """
        return [
            {
                "price_info": product.get_product_info_pos(
                                    product.lst_price, 1, int(pos_config_id)
                                )["all_prices"],
                "has_image": bool(product.image_1920),
                **product.read(
                    [
                        "id",
                        "display_name",
                        "description_sale",
                        "pos_categ_id",
                        "attribute_line_ids",
                    ]
                )[0],
            }
            for product in products_sudo
        ]
