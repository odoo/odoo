# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.misc import split_every
from werkzeug.urls import url_unquote


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_order_kiosk = fields.Boolean(related="pos_config_id.self_order_kiosk", readonly=False)
    pos_self_order_kiosk_mode = fields.Selection(related="pos_config_id.self_order_kiosk_mode", readonly=False)
    pos_self_order_kiosk_takeaway = fields.Boolean(related="pos_config_id.self_order_kiosk_takeaway", readonly=False)
    pos_self_order_kiosk_alternative_fp_id = fields.Many2one(related="pos_config_id.self_order_kiosk_alternative_fp_id", readonly=False)
    pos_self_order_kiosk_image_home_ids = fields.Many2many(related="pos_config_id.self_order_kiosk_image_home_ids", readonly=False)
    pos_self_order_kiosk_image_eat = fields.Image(related="pos_config_id.self_order_kiosk_image_eat", readonly=False)
    pos_self_order_kiosk_image_brand = fields.Image(related="pos_config_id.self_order_kiosk_image_brand", readonly=False)
    pos_self_order_kiosk_image_eat_name = fields.Char(related="pos_config_id.self_order_kiosk_image_eat_name", readonly=False)
    pos_self_order_kiosk_image_brand_name = fields.Char(related="pos_config_id.self_order_kiosk_image_brand_name", readonly=False)
    pos_self_order_kiosk_available_language_ids = fields.Many2many(related="pos_config_id.self_order_kiosk_available_language_ids", readonly=False)
    pos_self_order_kiosk_default_language = fields.Many2one(related="pos_config_id.self_order_kiosk_default_language", readonly=False)
    pos_self_order_view_mode = fields.Boolean(related="pos_config_id.self_order_view_mode", readonly=False)
    pos_self_order_table_mode = fields.Boolean(related="pos_config_id.self_order_table_mode", readonly=False)
    pos_self_order_pay_after = fields.Selection(related="pos_config_id.self_order_pay_after", readonly=False)
    pos_self_order_image = fields.Image(related="pos_config_id.self_order_image", readonly=False)
    pos_self_order_image_name = fields.Char(related="pos_config_id.self_order_image_name", readonly=False)

    @api.onchange("pos_self_order_kiosk_default_language", "pos_self_order_kiosk_available_language_ids")
    def _onchange_pos_self_order_kiosk_default_language(self):
        if self.pos_self_order_kiosk_default_language not in self.pos_self_order_kiosk_available_language_ids:
            self.pos_self_order_kiosk_available_language_ids = self.pos_self_order_kiosk_available_language_ids + self.pos_self_order_kiosk_default_language
        if not self.pos_self_order_kiosk_default_language and self.pos_self_order_kiosk_available_language_ids:
            self.pos_self_order_kiosk_default_language = self.pos_self_order_kiosk_available_language_ids[0]

    @api.onchange("pos_self_order_kiosk")
    def _self_order_kiosk_change(self):
        for record in self:
            record.is_kiosk_mode = record.pos_self_order_kiosk

            if record.pos_self_order_kiosk:
                record.pos_config_id.self_order_view_mode = False
                record.pos_config_id.self_order_table_mode = False

    # self_order_table_mode is only available if self_order_view_mode is True
    @api.onchange("pos_self_order_view_mode")
    def _onchange_pos_self_order_view_mode(self):
        if not self.pos_self_order_view_mode:
            self.pos_self_order_table_mode = False

    @api.onchange("pos_self_order_table_mode")
    def _onchange_pos_self_order_table_mode(self):
        if self.pos_self_order_table_mode:
            self.pos_self_order_view_mode = True

    def generate_qr_codes_page(self):
        """
        Generate the data needed to print the QR codes page
        """
        if self.pos_self_order_table_mode:
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
                'table_mode': self.pos_self_order_table_mode,
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
