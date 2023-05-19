# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Optional, List, Dict, Callable
from werkzeug.urls import url_quote
import base64


from odoo import api, fields, models, modules
from odoo.tools import file_open, split_every
from odoo.http import request

from odoo.addons.pos_self_order.controllers.utils import get_table_sudo
from odoo.addons.pos_self_order.models.product_product import ProductProduct
from odoo.addons.pos_self_order.models.pos_order import PosOrderLine
from odoo.addons.web.controllers.report import ReportController


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _self_order_default_image_name(self) -> str:
        return "default_background.jpg"

    def _self_order_default_image(self) -> bytes:
        image_path = modules.get_module_resource(
            "pos_self_order", "static/img", self._self_order_default_image_name()
        )
        return base64.b64encode(file_open(image_path, "rb").read())

    # TODO: i think it might make more sense to rename these fields to
    # is_qr_menu, is_self_order, is_kiosk

    self_order_view_mode = fields.Boolean(
        string="QR Code Menu",
        help="Allow customers to view the menu on their phones by scanning the QR code on the table",
    )
    self_order_table_mode = fields.Boolean(
        string="Self Order",
        help="Allow customers to Order from their phones",
    )
    self_order_kiosk_mode = fields.Boolean(
        string="Self Ordering Station",
        help="Turn this POS into a self ordering station",
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
    kiosk_qr_code = fields.Image(
        string="Kiosk QR Code",
        help="The qr code for the kiosk",
        compute="_compute_kiosk_qr_code",
        # store=True,
    )

    @api.depends("has_active_session")
    def _compute_kiosk_qr_code(self):
        for pos_config in self:
            print("salytare\n\n\n", pos_config.current_session_id.access_token)
            # FIXME: this always gives a qr code with the text "1234"
            old = pos_config.kiosk_qr_code
            pos_config.kiosk_qr_code = (
                pos_config.self_order_kiosk_mode
                and pos_config.has_active_session
                and base64.b64encode(
                    request.env["ir.actions.report"].barcode(
                        "QR",
                        pos_config.current_session_id.access_token,
                        width=200,
                        height=200,
                    )
                )
            )
            print("old and new:", old == pos_config.kiosk_qr_code)

    def _action_to_open_ui(self):
        should_open_ui = not self.self_order_kiosk_mode or self.has_active_session
        res = super()._action_to_open_ui()
        return should_open_ui and res

    def _compute_kiosk_url(self):
        for pos_config in self:
            pos_config.kiosk_url = (
                pos_config.self_order_kiosk_mode
                and pos_config.current_session_id
                and f"{pos_config._get_self_order_url()}?at={pos_config.current_session_id.access_token}"
            )

    @api.model_create_multi
    def create(self, vals_list):
        """
        We want self ordering to be enabled by default
        (This would have been nicer to do using a default value
        directly on the fields, but `module_pos_restaurant` would not be
        known at the time that the function for this default value would run)
        """
        for vals in vals_list:
            if vals.get("module_pos_restaurant"):
                vals.update(
                    {
                        "self_order_view_mode": True,
                        "self_order_table_mode": True,
                    }
                )
        return super().create(vals_list)

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
        if self.self_order_table_mode:
            access_token = (
                self.env["restaurant.table"]
                .search(
                    [("active", "=", True), *(table_id and [("id", "=", table_id)] or [])], limit=1
                )
                .access_token
            )
        elif self.self_order_kiosk_mode and self.current_session_id:
            access_token = self.current_session_id.access_token
        else:
            return base_route
        return f"{base_route}?at={access_token}"

    def _get_self_order_url(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        return url_quote(self.get_base_url() + self._get_self_order_route(table_id))

    def preview_self_order_app(self) -> Dict:
        """
        This function is called when the user clicks on the "Preview App" button
        :return: dict representing the action to open the app's url in a new tab
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
                        and [("pos_categ_id", "in", self.iface_available_categ_ids.ids)]
                        or []
                    ),
                ],
                order="pos_categ_id.sequence asc nulls last",
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
            "has_active_session": self.has_active_session,
            "orderline_unique_keys": PosOrderLine._get_unique_keys(),
            "is_kiosk": self.self_order_kiosk_mode,
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

    def _get_self_order_access_info(self, access_token: Optional[str] = None) -> Dict:
        """
        This function takes as a parameter the access_token provided
        in the http request and returns a specific dictionary
        if it finds that the access_token should grant access to ordering
        having the "access" dict in the frontend means that the client will be able to order
        """
        self.ensure_one()
        return (
            self._allows_self_ordering(access_token)
            and self.self_order_table_mode
            and {"access": get_table_sudo(table_access_token=access_token)._get_self_order_data()}
            or self.current_session_id.access_token == access_token
            and {
                "access": {
                    "id": self.id,
                    "name": self.id,
                    "access_token": access_token,
                }
            }
            or {}
        )

    def _allows_self_ordering(self, access_token: Optional[str] = None) -> bool:
        self.ensure_one()

        return self.has_active_session and (
            self.self_order_table_mode
            and get_table_sudo(table_access_token=access_token)
            or self.self_order_kiosk_mode
            and self.current_session_id.access_token == access_token
        )

    def _allows_qr_menu(self, access_token: Optional[str] = None) -> bool:
        return (
            self.self_order_view_mode == True
            or self.current_session_id.access_token == access_token
        )
