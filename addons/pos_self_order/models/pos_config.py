# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import uuid
import base64
from PIL import Image
from typing import Optional, List, Dict
from werkzeug.urls import url_quote
from odoo.tools import image_to_base64

from odoo import api, fields, models, modules, _
from odoo.tools import file_open, split_every


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _self_order_default_image_name(self) -> str:
        return "default_background.jpg"

    def _self_order_default_image(self) -> bytes:
        image_path = modules.get_module_resource(
            "pos_self_order", "static/img", self._self_order_default_image_name()
        )
        return base64.b64encode(file_open(image_path, "rb").read())

    def _self_order_kiosk_default_languages(self):
        return self.env["res.lang"].get_installed()

    status = fields.Selection(
        [("inactive", "Inactive"), ("active", "Active")],
        string="Status",
        compute="_compute_status",
        store=False,
    )
    self_order_kiosk_url = fields.Char(compute="_compute_self_order_kiosk_url")
    self_order_kiosk = fields.Boolean(
        string="Kiosk",
        help="Enable the kiosk mode for the Point of Sale",
    )
    self_order_kiosk_takeaway = fields.Boolean(
        string="Takeaway",
        help="Allow customers to order for takeaway",
    )
    self_order_kiosk_alternative_fp_id = fields.Many2one(
        'account.fiscal.position',
        string='Alternative Fiscal Position',
        help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.',
    )
    self_order_kiosk_mode = fields.Selection(
        [("counter", "Pickup Counter"), ("table", "Service at Table")],
        string="Kiosk Mode",
        default="counter",
        help="Choose the kiosk mode",
        required=True,
    )
    self_order_kiosk_available_language_ids = fields.Many2many(
        "res.lang",
        string="Available Languages",
        help="Languages available for the kiosk mode",
        default=_self_order_kiosk_default_languages,
    )
    self_order_kiosk_default_language = fields.Many2one(
        "res.lang",
        string="Default Language",
        help="Default language for the kiosk mode",
        default=lambda self: self.env["res.lang"].search(
            [("code", "=", self.env.lang)], limit=1
        ),
    )
    self_order_kiosk_image_home_ids = fields.Many2many(
        'ir.attachment',
        string="Home Images",
        help="Image to display on the self order screen",
    )
    self_order_kiosk_image_eat = fields.Image(
        string="Self Order Kiosk Image Eat",
        help="Image to display on the self order screen",
        max_width=1080,
        max_height=1920,
        default=_self_order_default_image,
    )
    self_order_kiosk_image_brand = fields.Image(
        string="Self Order Kiosk Image Brand",
        help="Image to display on the self order screen",
        max_width=1200,
        max_height=250,
    )
    self_order_kiosk_image_eat_name = fields.Char(
        string="Self Order Kiosk Image Eat Name",
        help="Name of the image to display on the self order screen",
        default=_self_order_default_image_name,
    )
    self_order_kiosk_image_brand_name = fields.Char(
        string="Self Order Kiosk Image Brand Name",
        help="Name of the image to display on the self order screen",
    )
    self_order_view_mode = fields.Boolean(
        string="QR Code Menu",
        help="Allow customers to view the menu on their phones by scanning the QR code on the table",
    )
    self_order_table_mode = fields.Boolean(
        string="Self Order",
        help="Allow customers to Order from their phones",
    )
    self_order_pay_after = fields.Selection(
        [("each", "Each Order (mobile payment only)"), ("meal", "Meal (mobile payment or cashier)")],
        string="Pay After:",
        default="meal",
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
        self.floor_ids.table_ids._update_identifier()

    @api.model
    def _init_access_token(self):
        pos_config_ids = self.env["pos.config"].search([])
        for pos_config_id in pos_config_ids:
            pos_config_id.access_token = self._get_access_token()

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
            for image_name in ['landing_01.jpg', 'landing_02.jpg', 'landing_03.jpg']:
                image_path = modules.get_module_resource("pos_self_order", "static/img", image_name)
                attachment = self.env['ir.attachment'].create({
                    'name': image_name,
                    'datas': base64.b64encode(file_open(image_path, "rb").read()),
                    'res_model': 'pos.config',
                    'res_id': pos_config_id.id,
                    'type': 'binary',
                })
                pos_config_id.self_order_kiosk_image_home_ids = [(4, attachment.id)]

            if pos_config_id.module_pos_restaurant:
                pos_config_id.self_order_view_mode = True
                pos_config_id.self_order_table_mode = True

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

    def _get_qr_code_data(self):
        self.ensure_one()

        table_qr_code = []
        if self.self_order_table_mode:
            table_qr_code.extend([{
                    'name': floor.name,
                    'type': 'table',
                    'tables': [
                        {
                            'identifier': table.identifier,
                            'id': table.id,
                            'name': table.name,
                            'url': self._get_self_order_url(table.id),
                        }
                        for table in floor.table_ids.filtered("active")
                    ]
                }
                for floor in self.floor_ids]
            )

        # Here we use "range" to determine the number of QR codes to generate from
        # this list, which will then be inserted into a PDF.
        table_qr_code.extend([{
            'name': 'Generic',
            'type': 'default',
            'tables': [{
                'id': i,
                'url': self._get_self_order_url(),
            } for i in range(0, 11)]
        }])

        return table_qr_code

    def _get_self_order_route(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        base_route = f"/menu/{self.id}"
        table_route = ""

        if not self.self_order_table_mode:
            return base_route

        table = self.env["restaurant.table"].search(
            [("active", "=", True), ("id", "=", table_id)], limit=1
        )

        if table:
            table_route = f"&table_identifier={table.identifier}"

        return f"{base_route}?access_token={self.access_token}{table_route}"

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

    def _get_available_products(self):
        self.ensure_one()
        return (
            self.env["product.product"]
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

    def _get_available_categories(self):
        self.ensure_one()
        return (
            self.env["pos.category"]
            .search(
                [
                    *(
                        self.limit_categories
                        and self.iface_available_categ_ids
                        and [("id", "in", self.iface_available_categ_ids.ids)]
                        or []
                    ),
                ],
                order="sequence",
            )
        )

    def _get_self_order_data(self) -> Dict:
        self.ensure_one()
        return {
            "pos_config_id": self.id,
            "iface_start_categ_id": self.iface_start_categ_id.id,
            "company_name": self.company_id.name,
            "company_color": self.company_id.color,
            "currency_id": self.currency_id.id,
            "show_prices_with_tax_included": self.iface_tax_included == "total",
            "custom_links": self._get_self_order_custom_links(),
            "products": self._get_available_products()._get_self_order_data(self),
            "combos": self._get_combos_data(),
            "pos_category": self._get_available_categories().read(["name", "sequence", "has_image"]),
            "has_active_session": self.has_active_session,
        }

    def _get_combos_data(self):
        self.ensure_one()
        combos = self.env["pos.combo"].search([])

        return[{
            'id': combo.id,
            'name': combo.name,
            'combo_line_ids': combo.combo_line_ids.read(['product_id', 'combo_price', 'lst_price', 'combo_id'])
        } for combo in combos]

    def _get_self_order_mobile_data(self):
        self.ensure_one()
        return {
            **self._get_self_order_data(),
            "mobile_image_home": self._get_kiosk_image(self.self_order_image),
        }

    def _get_self_order_kiosk_data(self):
        self.ensure_one()
        payment_search_params = self.current_session_id._loader_params_pos_payment_method()
        payment_methods = self.payment_method_ids.filtered(lambda p: p.use_payment_terminal == 'adyen').read(payment_search_params['search_params']['fields'])
        default_language = self.self_order_kiosk_default_language.read(["code", "name", "iso_code", "flag_image_url"])

        return {
            **self._get_self_order_data(),
            "avaiable_payment_methods": self.payment_method_ids.ids,
            "pos_payment_methods": payment_methods,
            "pos_session": self.current_session_id.read(["id", "access_token"])[0] if self.current_session_id else [],
            "kiosk_mode": self.self_order_kiosk_mode,
            "kiosk_takeaway": self.self_order_kiosk_takeaway,
            "kiosk_alternative_fp": self.self_order_kiosk_alternative_fp_id.id,
            "kiosk_image_home":  self._get_kiosk_attachment(self.self_order_kiosk_image_home_ids),
            "kiosk_image_eat": self._get_kiosk_image(self.self_order_kiosk_image_eat),
            "kiosk_image_brand": self._get_kiosk_image(self.self_order_kiosk_image_brand),
            "kiosk_default_language": default_language[0] if default_language else [],
            "kiosk_available_languages": self.self_order_kiosk_available_language_ids.read(["code", "display_name", "iso_code", "flag_image_url"]),
        }

    def _get_kiosk_image(self, image):
        image = Image.open(io.BytesIO(base64.b64decode(image))) if image else False
        return image_to_base64(image, 'PNG').decode('utf-8') if image else False

    def _get_kiosk_attachment(self, images):
        encoded_images = []
        for image in images:
            encoded_images.append({
                'id': image.id,
                'data': image.datas.decode('utf-8'),
            })
        return encoded_images

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

    def _compute_self_order_kiosk_url(self):
        for record in self:
            domain = self.get_base_url()
            record.self_order_kiosk_url = '%s/kiosk/%d?access_token=%s' % (domain, record.id, record.access_token)

    def action_close_kiosk_session(self):
        current_session_id = self.current_session_id

        if current_session_id:
            if current_session_id.order_ids:
                current_session_id.order_ids.filtered(lambda o: o.state not in ['paid', 'invoiced']).unlink()

            self.env['bus.bus']._sendone(f'pos_config-{self.access_token}', 'status', {
                'status': 'closed',
            })

            return current_session_id.action_pos_session_closing_control()

    def _compute_status(self):
        for record in self:
            record.status = 'active' if record.has_active_session else 'inactive'

    def action_open_kiosk(self):
        self.ensure_one()

        return {
            'name': _('Self Kiosk'),
            'type': 'ir.actions.act_url',
            'url': self.self_order_kiosk_url,
        }

    def action_open_wizard(self):
        self.ensure_one()

        if not self.current_session_id:
            pos_session = self.env['pos.session'].create({'user_id': self.env.uid, 'config_id': self.id})
            pos_session._ensure_access_token()
            self.env['bus.bus']._sendone(f'pos_config-{self.access_token}', 'status', {
                'status': 'open',
                'pos_session': pos_session.read(['id', 'access_token'])[0],
            })

        return {
            'name': _('Self Kiosk'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.config',
            'res_id': self.id,
            'target': 'new',
            'views': [(self.env.ref('pos_self_order.pos_self_order_kiosk_read_only_form_dialog').id, 'form')],
        }
