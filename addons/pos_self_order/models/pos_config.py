# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import uuid
import base64
from os.path import join as opj
from PIL import Image
from typing import Optional, List, Dict
from werkzeug.urls import url_quote
from odoo.exceptions import UserError
from odoo.tools import image_to_base64

from odoo import api, fields, models, _, service
from odoo.tools import file_open, split_every


class PosConfig(models.Model):
    _inherit = "pos.config"

    _ALLOWED_PAYMENT_METHODS = ['adyen', 'stripe']

    def _self_order_kiosk_default_languages(self):
        return self.env["res.lang"].get_installed()

    def _self_order_default_user(self):
        user_ids = self.env["res.users"].search(['|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)])
        for user_id in user_ids:
            if user_id.has_group("point_of_sale.group_pos_user") or user_id.has_group("point_of_sale.group_pos_manager"):
                return user_id

    status = fields.Selection(
        [("inactive", "Inactive"), ("active", "Active")],
        string="Status",
        compute="_compute_status",
        store=False,
    )
    self_ordering_url = fields.Char(compute="_compute_self_ordering_url")
    self_ordering_takeaway = fields.Boolean("Takeaway")
    self_ordering_alternative_fp_id = fields.Many2one(
        'account.fiscal.position',
        string='Alternative Fiscal Position',
        help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.',
    )
    self_ordering_mode = fields.Selection(
        [("nothing", "Disable"), ("consultation", "QR menu"), ("mobile", "QR menu + Ordering"), ("kiosk", "Kiosk")],
        string="Self Ordering Mode",
        default="nothing",
        help="Choose the self ordering mode",
        required=True,
    )
    self_ordering_service_mode = fields.Selection(
        [("counter", "Pickup zone"), ("table", "Table")],
        string="Service",
        default="counter",
        help="Choose the kiosk mode",
        required=True,
    )
    self_ordering_default_language_id = fields.Many2one(
        "res.lang",
        string="Default Language",
        help="Default language for the kiosk mode",
        default=lambda self: self.env["res.lang"].search(
            [("code", "=", self.env.lang)], limit=1
        ),
    )
    self_ordering_available_language_ids = fields.Many2many(
        "res.lang",
        string="Available Languages",
        help="Languages available for the kiosk mode",
        default=_self_order_kiosk_default_languages,
    )
    self_ordering_image_home_ids = fields.Many2many(
        'ir.attachment',
        string="Add images",
        help="Image to display on the self order screen",
    )
    self_ordering_default_user_id = fields.Many2one(
        "res.users",
        string="Default User",
        help="Access rights of this user will be used when visiting self order website when no session is open.",
        default=_self_order_default_user,
    )
    self_ordering_pay_after = fields.Selection(
        selection=lambda self: self._compute_selection_pay_after(),
        string="Pay After:",
        default="meal",
        help="Choose when the customer will pay",
        required=True,
    )
    self_ordering_image_brand = fields.Image(
        string="Self Order Kiosk Image Brand",
        help="Image to display on the self order screen",
        max_width=1200,
        max_height=250,
    )
    self_ordering_image_brand_name = fields.Char(
        string="Self Order Kiosk Image Brand Name",
        help="Name of the image to display on the self order screen",
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
        pos_config_ids = super().create(vals_list)

        for pos_config_id in pos_config_ids:
            for image_name in ['landing_01.jpg', 'landing_02.jpg', 'landing_03.jpg']:
                image_path = opj("pos_self_order/static/img", image_name)
                attachment = self.env['ir.attachment'].create({
                    'name': image_name,
                    'datas': base64.b64encode(file_open(image_path, "rb").read()),
                    'res_model': 'pos.config',
                    'res_id': pos_config_id.id,
                    'type': 'binary',
                })
                pos_config_id.self_ordering_image_home_ids = [(4, attachment.id)]

            self.env['pos_self_order.custom_link'].create({
                'name': _('Order Now'),
                'url': f'/pos-self/{pos_config_id.id}/products',
                'pos_config_ids': [(4, pos_config_id.id)],
            })

            if pos_config_id.module_pos_restaurant:
                pos_config_id.self_ordering_mode = 'mobile'

        return pos_config_ids

    def _get_allowed_payment_methods(self):
        if self.self_ordering_mode == 'kiosk':
            return self.payment_method_ids.filtered(lambda p: p.use_payment_terminal in self._ALLOWED_PAYMENT_METHODS)
        return []

    def write(self, vals):
        for record in self:
            if vals.get('self_ordering_mode') == 'kiosk' or (vals.get('pos_self_ordering_mode') == 'mobile' and vals.get('pos_self_ordering_service_mode') == 'counter'):
                vals['self_ordering_pay_after'] = 'each'

            if (not vals.get('module_pos_restaurant') and not record.module_pos_restaurant) and vals.get('self_ordering_mode') == 'mobile':
                vals['self_ordering_pay_after'] = 'each'

            if (vals.get('self_ordering_service_mode') == 'counter' or record.self_ordering_service_mode == 'counter') and vals.get('self_ordering_mode') == 'mobile':
                vals['self_ordering_pay_after'] = 'each'

            if vals.get('self_ordering_mode') == 'mobile' and vals.get('self_ordering_pay_after') == 'meal':
                vals['self_ordering_service_mode'] = 'table'
        return super().write(vals)

    @api.depends("module_pos_restaurant")
    def _compute_self_order(self):
        for record in self:
            if not record.module_pos_restaurant and record.self_ordering_mode != 'kiosk':
                record.self_ordering_mode = 'nothing'

    def _compute_selection_pay_after(self):
        selection_each_label = _("Each Order")
        version_info = service.common.exp_version()['server_version_info']
        if version_info[-1] == '':
            selection_each_label = f"{selection_each_label} {_('(require Odoo Enterprise)')}"
        return [("meal", _("Meal")), ("each", selection_each_label)]

    @api.constrains('self_ordering_default_user_id')
    def _check_default_user(self):
        for record in self:
            if record.self_ordering_mode == 'mobile' and not record.self_ordering_default_user_id.has_group("point_of_sale.group_pos_user") and not record.self_ordering_default_user_id.has_group("point_of_sale.group_pos_manager"):
                raise UserError(_("The Self-Order default user must be a POS user"))

    def _get_qr_code_data(self):
        self.ensure_one()

        table_qr_code = []
        if self.self_ordering_mode == 'mobile' and self.module_pos_restaurant and self.self_ordering_service_mode == 'table':
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
        else:
            # Here we use "range" to determine the number of QR codes to generate from
            # this list, which will then be inserted into a PDF.
            table_qr_code.extend([{
                'name': _('Generic'),
                'type': 'default',
                'tables': [{
                    'id': i,
                    'url': self._get_self_order_url(),
                } for i in range(0, 6)]
            }])

        return table_qr_code

    def _get_self_order_route(self, table_id: Optional[int] = None) -> str:
        self.ensure_one()
        base_route = f"/pos-self/{self.id}"
        table_route = ""

        if self.self_ordering_mode == 'consultation':
            return base_route

        if self.self_ordering_mode == 'mobile':
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
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self._get_self_order_route(),
            "target": "new",
        }

    def _get_self_order_custom_links(self):
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
        combo_product_ids = self.env["product.product"].search([
            ("detailed_type", "=", 'combo'),
            *(
                self.limit_categories
                and self.iface_available_categ_ids
                and [("pos_categ_ids", "in", self.iface_available_categ_ids.ids)]
                or []
            ),
        ])
        product_ids = combo_product_ids.combo_ids.combo_line_ids.product_id

        available_product_ids = (
            self.env["product.product"]
            .search(
                [
                    ("id", "not in", product_ids.ids),
                    ("available_in_pos", "=", True),
                    ("self_order_available", "=", True),
                    *(
                        self.limit_categories
                        and self.iface_available_categ_ids
                        and [("pos_categ_ids", "in", self.iface_available_categ_ids.ids)]
                        or []
                    ),
                ],
            )
        )

        return product_ids + available_product_ids

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

    def _get_kitchen_printer(self):
        self.ensure_one()
        printerData = {}
        for printer in self.printer_ids:
            printerData[printer.id] = {
                "printer_type": printer.printer_type,
                "proxy_ip": printer.proxy_ip,
                "product_categories_ids": printer.product_categories_ids.ids,
            }
        return printerData

    def _get_self_ordering_payment_methods_data(self, payment_methods):
        excluded_fields = ['image']
        payment_search_fields = self.current_session_id._loader_params_pos_payment_method()['search_params']['fields']
        filtered_fields = [field for field in payment_search_fields if field not in excluded_fields]
        return payment_methods.read(filtered_fields)

    def _get_self_ordering_data(self):
        self.ensure_one()
        payment_methods = self._get_self_ordering_payment_methods_data(self._get_allowed_payment_methods())
        default_language = self.self_ordering_default_language_id.read(["code", "name", "iso_code", "flag_image_url"])

        return {
            "pos_config_id": self.id,
            "pos_session": self.current_session_id.read(["id", "access_token"])[0] if self.current_session_id and self.current_session_id.state == 'opened' else False,
            "company": {
                **self.company_id.read(["name", "email", "website", "vat", "name", "phone", "point_of_sale_use_ticket_qr_code", "point_of_sale_ticket_unique_code"])[0],
                "partner_id": [None, self.company_id.partner_id.contact_address],
                "country": self.company_id.country_id.read(["vat_label"])[0],
            },
            "base_url": self.get_base_url(),
            "custom_links": self._get_self_order_custom_links(),
            "currency_id": self.currency_id.id,
            "pos_payment_methods": payment_methods if self.self_ordering_mode == "kiosk" else [],
            "currency_decimals": self.currency_id.decimal_places,
            "pos_category": self._get_available_categories().read(["name", "sequence", "has_image"]),
            "products": self._get_available_products()._get_self_order_data(self),
            "combos": self._get_combos_data(),
            "config": {
                "iface_start_categ_id": self.iface_start_categ_id.id,
                "iface_tax_included": self.iface_tax_included == "total",
                "self_ordering_mode": self.self_ordering_mode,
                "self_ordering_takeaway": self.self_ordering_takeaway,
                "self_ordering_service_mode": self.self_ordering_service_mode,
                "self_ordering_default_language_id": default_language[0] if default_language else [],
                "self_ordering_available_language_ids":  self.self_ordering_available_language_ids.read(["code", "display_name", "iso_code", "flag_image_url"]),
                "self_ordering_image_home_ids": self._get_self_ordering_attachment(self.self_ordering_image_home_ids),
                "self_ordering_image_brand": self._get_self_ordering_image(self.self_ordering_image_brand),
                "self_ordering_pay_after": self.self_ordering_pay_after,
                "receipt_header": self.receipt_header,
                "receipt_footer": self.receipt_footer,
            },
            "kitchen_printers": self._get_kitchen_printer(),
        }

    def _get_combos_data(self):
        self.ensure_one()
        combos = self.env["pos.combo"].search([])

        return[{
            'id': combo.id,
            'name': combo.name,
            'combo_line_ids': combo.combo_line_ids.read(['product_id', 'combo_price', 'lst_price', 'combo_id'])
        } for combo in combos]


    def _get_self_ordering_image(self, image):
        image = Image.open(io.BytesIO(base64.b64decode(image))) if image else False
        return image_to_base64(image, 'PNG').decode('utf-8') if image else False

    def _get_self_ordering_attachment(self, images):
        encoded_images = []
        for image in images:
            encoded_images.append({
                'id': image.id,
                'data': image.sudo().datas.decode('utf-8'),
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

    def _compute_self_ordering_url(self):
        for record in self:
            record.self_ordering_url = self.get_base_url() + self._get_self_order_route()

    def action_close_kiosk_session(self):
        current_session_id = self.current_session_id

        if current_session_id:
            if current_session_id.order_ids:
                current_session_id.order_ids.filtered(lambda o: o.state not in ['paid', 'invoiced']).unlink()

            self.env['bus.bus']._sendone(f'pos_config-{self.access_token}', 'STATUS', {
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
            'url': self._get_self_order_route(),
        }

    def action_open_wizard(self):
        self.ensure_one()

        if not self.current_session_id:
            pos_session = self.env['pos.session'].create({'user_id': self.env.uid, 'config_id': self.id})
            pos_session._ensure_access_token()
            self.env['bus.bus']._sendone(f'pos_config-{self.access_token}', 'STATUS', {
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
