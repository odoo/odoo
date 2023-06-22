# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Optional, List, Dict, Callable
from werkzeug.urls import url_quote
import base64


from odoo import api, fields, models, modules
from odoo.tools import file_open, split_every

from odoo.addons.pos_self_order.models.product_product import ProductProduct
from odoo.addons.pos_self_order.models.pos_order import PosOrderLine


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _self_order_default_image_name(self) -> str:
        return "default_background.jpg"

    def _self_order_default_image(self) -> bytes:
        image_path = modules.get_module_resource(
            "pos_self_order", "static/img", self._self_order_default_image_name()
        )
        return base64.b64encode(file_open(image_path, "rb").read())

    self_order_view_mode = fields.Boolean(
        string="QR Code Menu",
        help="Allow customers to view the menu on their phones by scanning the QR code on the table",
    )
    self_order_table_mode = fields.Boolean(
        string="Self Order",
        help="Allow customers to Order from their phones",
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
    )
    self_order_image_name = fields.Char(
        string="Self Order Image Name",
        help="Name of the image to display on the self order screen",
        default=_self_order_default_image_name,
    )

    @api.model_create_multi
    def create(self, vals_list):
        """
        We want self ordering to be enabled by default
        (This would have been nicer to do using a default value
        directly on the fields, but `module_pos_restaurant` would not be
        known at the time that the function for this default value would run)
        """
        pos_config_ids = super().create(vals_list)

        for pos_config_id in pos_config_ids:
            if pos_config_id.module_pos_restaurant:
                pos_config_id.self_order_view_mode = True
                pos_config_id.self_order_table_mode = True

                self.env['pos_self_order.custom_link'].create({
                    'url': '/menu/%s/products' % pos_config_id.id,
                    'name': 'View Menu',
                    'pos_config_ids': pos_config_id,
                    'style': 'primary',
                })

        return pos_config_ids

    @api.depends("module_pos_restaurant")
    def _compute_self_order(self):
        """
        Self ordering will only be enabled for restaurants
        """
        for record in self:
            if not record.module_pos_restaurant:
                record.self_order_view_mode = False
                record.self_order_table_mode = False

    def _get_self_order_route(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        base_route = f"/menu/{self.id}"
        if not self.self_order_table_mode:
            return base_route
        access_token = (
            self.env["restaurant.table"]
            .search(
                [("active", "=", True), *(table_id and [("id", "=", table_id)] or [])], limit=1
            )
            .access_token
        )
        return f"{base_route}?at={access_token}"

    def _get_self_order_url(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        return url_quote(self.get_base_url() + self._get_self_order_route(table_id))

    def preview_self_order_app(self):
        """
        This function is called when the user clicks on the "Preview App" button
        :return: object representing the action to open the app's url in a new tab
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self._get_self_order_route(),
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
                        and [("pos_categ_ids", "in", self.iface_available_categ_ids.ids)]
                        or []
                    ),
                ],
            )
        )

    def _get_self_order_data(self) -> Dict:
        self.ensure_one()
        return {
            "pos_config_id": self.id,
            "company_name": self.company_id.name,
            "currency_id": self.currency_id.id,
            "show_prices_with_tax_included": self.iface_tax_included == "total",
            "custom_links": self._get_self_order_custom_links(),
            "products": self._get_available_products()._get_self_order_data(self),
            "pos_category": self.env['pos.category'].sudo().search_read(fields=["name", "sequence"], order="sequence"),
            "has_active_session": self.has_active_session,
        }

    def _generate_data_for_qr_codes_page(self, cols: int = 4) -> Dict[str, List[Dict]]:
        """
        :cols: the number of qr codes per row
        """
        self.ensure_one()
        return {
            "floors": self._split_qr_codes_list(
                self._get_qr_codes_info(cols * cols),
                cols,
            )
        }

    def _get_qr_codes_info(self, total_number: int) -> List[Dict]:
        """
        total_number: the number of qr codes to generate (in the case where we don't have
                floor management)
        return: a list of dictionaries with the following keys:
            - name: the name of the floor
            - tables: a list of dictionaries with the following keys:
                - id: the id of the table
                - url: the url of the table
                - name?: the name of the table
        """
        self.ensure_one()
        if self.self_order_table_mode:
            return self.floor_ids._get_data_for_qr_codes_page(self._get_self_order_url)
        else:
            return self._get_default_qr_codes(total_number, self._get_self_order_url)

    def _split_qr_codes_list(self, floors: List[Dict], cols: int) -> List[Dict]:
        """
        :floors: the list of floors
        :cols: the number of qr codes per row
        """
        self.ensure_one()
        return [
            {
                "name": floor.get("name"),
                "rows_of_tables": list(split_every(cols, floor["tables"], list)),
            }
            for floor in floors
        ]

    def _get_default_qr_codes(
        self, number: int, url: Callable[[Optional[int]], str]
    ) -> List[Dict]:
        """
        :number: the number of qr codes to generate
        :url: a function that takes a table id and returns the url of the table
        """
        self.ensure_one()
        return [
            {
                "tables": [
                    {
                        "id": 0,
                        "url": url(),
                    }
                ]
                * number,
            }
        ]
