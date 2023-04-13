# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Optional, List, Dict
import base64

from odoo import api, fields, models, modules

from odoo.addons.pos_self_order.models.product_product import ProductProduct


class PosConfig(models.Model):
    _inherit = "pos.config"


    def _self_order_default_image_name(self) -> str:
        return "default_background.jpg"
# FIXME: this image does not get applied to the demo data pos
    def _self_order_default_image(self) -> bytes:
        image_path = modules.get_module_resource(
            "pos_self_order", "static/img", self._self_order_default_image_name()
        )
        return base64.b64encode(open(image_path, "rb").read())

    self_order_view_mode = fields.Boolean(
        string="QR Code Menu",
        help="Allow customers to view the menu on their phones by scanning the QR code on the table",
        compute="_compute_self_order",
        store=True,
    )
    self_order_table_mode = fields.Boolean(
        string="Self Order",
        help="Allow customers to Order from their phones",
        compute="_compute_self_order",
        store=True,
    )
    self_order_pay_after = fields.Selection(
        [("each", "Each Order"), ("meal", "Meal")],
        string="Pay After:",
        default="each",
        help="Choose when the customer will pay",
        required=True,
    )
    self_order_image = fields.Image(
        string="Self Order Image",
        help="Image to display on the self order screen",
        max_width=1920,
        max_height=1080,
        default=_self_order_default_image,
        store=True,
    )
    self_order_image_name = fields.Char(
        string="Self Order Image Name",
        help="Name of the image to display on the self order screen",
        default=_self_order_default_image_name,
        store=True,
    )

    @api.depends("module_pos_restaurant")
    def _compute_self_order(self):
        for record in self:
            record.self_order_view_mode = record.module_pos_restaurant
            record.self_order_table_mode = record.module_pos_restaurant

    def self_order_route(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        base_route = f"/menu/{self.id}"
        if not self.self_order_table_mode:
            return base_route
        table_access_token = (
            self.env["restaurant.table"]
            .search(
                [("active", "=", True), *(table_id and [("id", "=", table_id)] or [])], limit=1
            )
            .access_token
        )
        return f"{base_route}?id={table_access_token}"

    def preview_self_order_app(self):
        """
        This function is called when the user clicks on the "Preview App" button
        :return: object representing the action to open the app's url in a new tab
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.self_order_route(),
            "target": "new",
        }

    def _get_self_order_custom_links(self) -> List[Dict[str, str]]:
        """
        On the landing page of the app we can have a number of custom links
        that are defined by the restaurant employee in the backend.
        This function returns a list of dictionaries with the attributes of each link
        that is available for the POS with id pos_config_id.
        """
        self.ensure_one()
        return (
            self.env["pos_self_order.custom_link"]
            .sudo()
            .search_read(
                [
                    "|",
                    ("pos_config_ids", "in", [self.id]),
                    ("pos_config_ids", "=", False),
                ],
                fields=["name", "url", "style"],
                order="sequence",
            )
        )

    def _get_available_products(self) -> ProductProduct:
        """
        This function returns the products that are available in the given PosConfig
        """
        self.ensure_one()
        return (
            self.env["product.product"]
            .sudo()
            .search(
                [
                    ("available_in_pos", "=", True),
                    *(
                        self.limit_categories
                        and self.iface_available_categ_ids
                        and [("pos_categ_id", "in", self.iface_available_categ_ids.ids)]
                        or []
                    ),
                ],
                order="pos_categ_id.sequence asc nulls last",
            )
        )
