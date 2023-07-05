# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import List, Dict
import uuid
import base64

from odoo import api, fields, models, modules
from odoo.tools import file_open

from odoo.addons.pos_self_order.models.product_product import ProductProduct


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
        help="Allow customers to view the menu on their phones by scanning the QR code",
    )
    self_order_ordering_mode = fields.Boolean(
        string="Self Order",
        help="Allow customers to Order from their phones",
    )
    self_order_pay_after = fields.Selection(
        [("each", "Each Order")],
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
    access_token = fields.Char(
        "Security Token",
        copy=False,
        required=True,
        readonly=True,
        default=lambda self: self._get_access_token(),
    )

    @staticmethod
    def _get_access_token():
        return uuid.uuid4().hex[:16]

    def _update_access_token(self):
        self.access_token = self._get_access_token()

    @api.model
    def _init_access_token(self):
        pos_config_ids = self.env["pos.config"].search([])
        for pos_config_id in pos_config_ids:
            pos_config_id.access_token = self._get_access_token()

    def _get_self_order_route(self) -> str:
        self.ensure_one()
        base_route = f"/menu/{self.id}"

        if not self.self_order_ordering_mode:
            return base_route

        return self.get_base_url() + f"{base_route}?access_token={self.access_token}"

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
        that are defined by the employee in the backend.
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

    def _generate_qr_code(self):
        qr_code = {
            'data': [
                {
                    'name': 'Generics QR code',
                    'qr_codes':[{
                        'name': 'Generic',
                        'url': self._get_self_order_route(),
                    } for x in range(0, 12)]
                }
            ]
        }

        return qr_code
