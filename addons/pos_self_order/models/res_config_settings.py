# -*- coding: utf-8 -*-

import qrcode
import zipfile
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import split_every
from odoo.osv.expression import AND
from werkzeug.urls import url_unquote


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_ordering_takeaway = fields.Boolean(related="pos_config_id.self_ordering_takeaway", readonly=False)
    pos_self_ordering_service_mode = fields.Selection(related="pos_config_id.self_ordering_service_mode", readonly=False, required=True)
    pos_self_ordering_mode = fields.Selection(related="pos_config_id.self_ordering_mode", readonly=False, required=True)
    pos_self_ordering_default_language_id = fields.Many2one(related="pos_config_id.self_ordering_default_language_id", readonly=False)
    pos_self_ordering_available_language_ids = fields.Many2many(related="pos_config_id.self_ordering_available_language_ids", readonly=False)
    pos_self_ordering_image_home_ids = fields.Many2many(related="pos_config_id.self_ordering_image_home_ids", readonly=False)
    pos_self_ordering_image_brand = fields.Image(related="pos_config_id.self_ordering_image_brand", readonly=False)
    pos_self_ordering_image_brand_name = fields.Char(related="pos_config_id.self_ordering_image_brand_name", readonly=False)
    pos_self_ordering_pay_after = fields.Selection(related="pos_config_id.self_ordering_pay_after", readonly=False, required=True)
    pos_self_ordering_default_user_id = fields.Many2one(related="pos_config_id.self_ordering_default_user_id", readonly=False)

    @api.onchange("pos_self_ordering_default_user_id")
    def _onchange_default_user(self):
        self.ensure_one()
        if self.pos_self_ordering_default_user_id and self.pos_self_ordering_mode == 'mobile':
            user = self.pos_self_ordering_default_user_id
            if not (user.has_group("point_of_sale.group_pos_user")
                    or user.has_group("point_of_sale.group_pos_manager")):
                raise ValidationError(_("The user must be a POS user"))

    @api.onchange("pos_self_ordering_service_mode")
    def _onchange_pos_self_order_service_mode(self):
        if self.pos_self_ordering_service_mode == 'counter':
            self.pos_self_ordering_pay_after = "each"

    @api.onchange("pos_self_ordering_default_language_id", "pos_self_ordering_available_language_ids")
    def _onchange_pos_self_order_kiosk_default_language(self):
        if self.pos_self_ordering_default_language_id not in self.pos_self_ordering_available_language_ids:
            self.pos_self_ordering_available_language_ids = self.pos_self_ordering_available_language_ids + self.pos_self_ordering_default_language_id
        if not self.pos_self_ordering_default_language_id and self.pos_self_ordering_available_language_ids:
            self.pos_self_ordering_default_language_id = self.pos_self_ordering_available_language_ids[0]

    @api.onchange("pos_self_ordering_mode", "pos_module_pos_restaurant")
    def _onchange_pos_self_order_kiosk(self):
        if self.pos_self_ordering_mode == 'kiosk':
            self.is_kiosk_mode = True
            self.pos_module_pos_restaurant = False
            self.pos_self_ordering_pay_after = "each"
            cash_payment_methods = self.pos_payment_method_ids.filtered(lambda x: x.is_cash_count)
            self.pos_payment_method_ids = self.pos_payment_method_ids - cash_payment_methods
        else:
            self.is_kiosk_mode = False

            if not self.pos_module_pos_restaurant:
                self.pos_self_ordering_service_mode = 'counter'

    @api.onchange("pos_payment_method_ids")
    def _onchange_pos_payment_method_ids(self):
        if self.pos_self_ordering_mode == 'kiosk' and any(pm.is_cash_count for pm in self.pos_payment_method_ids):
            raise ValidationError(_("You cannot add cash payment methods in kiosk mode."))

    @api.onchange("pos_self_ordering_pay_after", "pos_self_ordering_mode")
    def _onchange_pos_self_order_pay_after(self):
        if self.pos_self_ordering_pay_after == "meal" and self.pos_self_ordering_mode == 'kiosk':
            raise ValidationError(_("Only pay after each is available with kiosk mode."))

        if self.pos_self_ordering_service_mode == 'counter' and self.pos_self_ordering_mode == 'mobile':
            self.pos_self_ordering_pay_after = "each"

        if self.pos_self_ordering_mode not in ['nothing', 'consultation'] and self.pos_self_ordering_pay_after == "each" and not self.module_pos_preparation_display:
            self.module_pos_preparation_display = True

    def custom_link_action(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "pos_self_order.custom_link",
            "views": [[False, "list"]],
            "domain": ['|', ['pos_config_ids', 'in', self.pos_config_id.id], ["pos_config_ids", "=", False]],
        }

    def __generate_single_qr_code(self, url):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        return qr.make_image(fill_color="black", back_color="transparent")

    def generate_qr_codes_zip(self):
        if not self.pos_self_ordering_mode in ['mobile', 'consultation']:
            raise ValidationError(_("QR codes can only be generated in mobile or consultation mode."))

        qr_images = []

        if self.pos_module_pos_restaurant:
            table_ids = self.pos_config_id.floor_ids.table_ids

            if not table_ids:
                raise ValidationError(_("In Self-Order mode, you must have at least one table to generate QR codes"))

            for table in table_ids:
                qr_images.append({
                    'image': self.__generate_single_qr_code(url_unquote(self.pos_config_id._get_self_order_url(table.id))),
                    'name': f"{table.floor_id.name} - {table.table_number}",
                })
        else:
            qr_images.append({
                'image': self.__generate_single_qr_code(url_unquote(self.pos_config_id._get_self_order_url())),
                'name': "generic",
            })

        # Create a zip with all images in qr_images
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", 0) as zip_file:
            for index, qr_image in enumerate(qr_images):
                with zip_file.open(f"{qr_image['name']} ({index + 1}).png", "w") as buf:
                    qr_image['image'].save(buf, format="PNG")
        zip_buffer.seek(0)

        # Delete previous attachments
        self.env["ir.attachment"].search([
            ("name", "=", "self_order_qr_code.zip"),
        ]).unlink()

        # Create an attachment with the zip
        attachment_id = self.env["ir.attachment"].create({
            "name": "self_order_qr_code.zip",
            "type": "binary",
            "raw": zip_buffer.read(),
            "res_model": self._name,
            "res_id": self.id,
        })

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment_id.id}",
            "target": "new",
        }

    def generate_qr_codes_page(self):
        """
        Generate the data needed to print the QR codes page
        """
        if self.pos_self_ordering_mode == 'mobile' and self.pos_module_pos_restaurant:
            table_ids = self.pos_config_id.floor_ids.table_ids

            if not table_ids:
                raise ValidationError(_("In Self-Order mode, you must have at least one table to generate QR codes"))

            url = url_unquote(self.pos_config_id._get_self_order_url(table_ids[0].id))
            name = table_ids[0].table_number
        else:
            url = url_unquote(self.pos_config_id._get_self_order_url())
            name = ""

        return self.env.ref("pos_self_order.report_self_order_qr_codes_page").report_action(
            [], data={
                'pos_name': self.pos_config_id.name,
                'floors': [
                    {
                        "name": floor.get("name"),
                        "type": floor.get("type"),
                        "table_rows": list(split_every(3, floor["tables"], list)),
                    }
                    for floor in self.pos_config_id._get_qr_code_data()
                ],
                'table_mode': self.pos_self_ordering_mode and self.pos_module_pos_restaurant and self.pos_self_ordering_service_mode == 'table',
                'self_order': self.pos_self_ordering_mode == 'mobile',
                'table_example': {
                    'name': name,
                    'decoded_url': url or "",
                }
            }
        )

    def preview_self_order_app(self):
        self.ensure_one()
        return self.pos_config_id.preview_self_order_app()

    def update_access_tokens(self):
        self.ensure_one()
        self.pos_config_id._update_access_token()

    @api.depends('pos_self_ordering_mode')
    def _compute_pos_pricelist_id(self):
        super()._compute_pos_pricelist_id()
        for res_config in self:
            if res_config.pos_self_ordering_mode == 'kiosk':
                currency_id = res_config.pos_journal_id.currency_id.id if res_config.pos_journal_id.currency_id else res_config.pos_config_id.company_id.currency_id.id
                domain = AND([self.env['product.pricelist']._check_company_domain(res_config.pos_config_id.company_id), [('currency_id', '=', currency_id)]])
                res_config.pos_available_pricelist_ids = self.env['product.pricelist'].search(domain)
