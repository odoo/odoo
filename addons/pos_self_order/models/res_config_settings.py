# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import split_every
from werkzeug.urls import url_unquote


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_ordering_takeaway = fields.Boolean(related="pos_config_id.self_ordering_takeaway", readonly=False)
    pos_self_ordering_service_mode = fields.Selection(related="pos_config_id.self_ordering_service_mode", readonly=False)
    pos_self_ordering_mode = fields.Selection(related="pos_config_id.self_ordering_mode", readonly=False)
    pos_self_ordering_alternative_fp_id = fields.Many2one(related="pos_config_id.self_ordering_alternative_fp_id", readonly=False)
    pos_self_ordering_default_language_id = fields.Many2one(related="pos_config_id.self_ordering_default_language_id", readonly=False)
    pos_self_ordering_available_language_ids = fields.Many2many(related="pos_config_id.self_ordering_available_language_ids", readonly=False)
    pos_self_ordering_image_home_ids = fields.Many2many(related="pos_config_id.self_ordering_image_home_ids", readonly=False)
    pos_self_ordering_image_brand = fields.Image(related="pos_config_id.self_ordering_image_brand", readonly=False)
    pos_self_ordering_image_brand_name = fields.Char(related="pos_config_id.self_ordering_image_brand_name", readonly=False)
    pos_self_ordering_pay_after = fields.Selection(related="pos_config_id.self_ordering_pay_after", readonly=False)
    pos_self_ordering_default_user_id = fields.Many2one(related="pos_config_id.self_ordering_default_user_id", readonly=False)

    @api.onchange("pos_self_ordering_default_user_id")
    def _onchange_default_user(self):
        self.ensure_one()
        if self.pos_self_ordering_default_user_id and self.pos_self_ordering_mode == 'mobile':
            user_id = self.pos_self_ordering_default_user_id

            if not user_id.has_group("point_of_sale.group_pos_user") and not user_id.has_group("point_of_sale.group_pos_manager"):
                raise UserError(_("The user must be a POS user"))

    @api.onchange("pos_self_ordering_default_language_id", "pos_self_ordering_available_language_ids")
    def _onchange_pos_self_order_kiosk_default_language(self):
        if self.pos_self_ordering_default_language_id not in self.pos_self_ordering_available_language_ids:
            self.pos_self_ordering_available_language_ids = self.pos_self_ordering_available_language_ids + self.pos_self_ordering_default_language_id
        if not self.pos_self_ordering_default_language_id and self.pos_self_ordering_available_language_ids:
            self.pos_self_ordering_default_language_id = self.pos_self_ordering_available_language_ids[0]

    @api.onchange("pos_self_ordering_mode")
    def _onchange_pos_self_order_kiosk(self):
        if self.pos_self_ordering_mode == 'kiosk':
            self.is_kiosk_mode = True
            self.pos_self_ordering_pay_after = "each"

        elif self.pos_self_ordering_mode == 'mobile' and not self.pos_module_pos_restaurant:
            raise UserError(_("In Self-Order mode, you must have the Restaurant module"))
        else:
            self.is_kiosk_mode = False

    @api.onchange("pos_self_ordering_pay_after", "pos_self_ordering_mode")
    def _onchange_pos_self_order_pay_after(self):
        if self.pos_self_ordering_pay_after == "meal" and self.pos_self_ordering_mode == 'kiosk':
            raise UserError(_("Only pay after each is available with kiosk mode."))

        if self.pos_self_ordering_pay_after == "each" and not self.module_pos_preparation_display:
            self.module_pos_preparation_display = True

    @api.onchange("pos_self_ordering_service_mode")
    def _onchange_pos_self_ordering_service_mode(self):
        table_ids = self.pos_config_id.floor_ids.table_ids
        if self.pos_self_ordering_service_mode == 'table' and self.pos_self_ordering_mode == 'mobile' and not table_ids:
            raise UserError(_("In Self-Order mode, you must have at least one table to use the table service mode"))

    def generate_qr_codes_page(self):
        """
        Generate the data needed to print the QR codes page
        """
        if self.pos_self_ordering_mode == 'mobile':
            table_ids = self.pos_config_id.floor_ids.table_ids

            if not table_ids:
                raise UserError(_("In Self-Order mode, you must have at least one table to generate QR codes"))

            url = url_unquote(self.pos_config_id._get_self_order_url(table_ids[0].id))
            name = table_ids[0].name
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
                'table_mode': self.pos_self_ordering_mode,
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
