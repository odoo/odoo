# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_order_view_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_ordering_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_pay_after = fields.Selection(
        [("each", "Each Order")],
        string="Pay After:",
        default="each",
        help="Choose when the customer will pay",
        readonly=False,
        required=True,
    )
    pos_self_order_image = fields.Image(
        compute="_compute_pos_module_pos_self_order",
        store=True,
        readonly=False,
        max_width=1920,
        max_height=1080,
    )
    pos_self_order_image_name = fields.Char(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )

    @api.depends("pos_config_id")
    def _compute_pos_module_pos_self_order(self):
        for res_config in self:
            if not res_config.pos_config_id.self_order_view_mode:
                res_config.update(
                    {
                        "pos_self_order_view_mode": False,
                        "pos_self_order_ordering_mode": False,
                        "pos_self_order_pay_after": "each",
                        "pos_self_order_image": False,
                        "pos_self_order_image_name": False,
                    }
                )
            else:
                res_config.update(
                    {
                        "pos_self_order_view_mode": res_config.pos_config_id.self_order_view_mode,
                        "pos_self_order_ordering_mode": res_config.pos_config_id.self_order_ordering_mode,
                        "pos_self_order_pay_after": res_config.pos_config_id.self_order_pay_after,
                        "pos_self_order_image": res_config.pos_config_id.self_order_image,
                        "pos_self_order_image_name": res_config.pos_config_id.self_order_image_name,
                    }
                )

    # self_order_ordering_mode is only available if self_order_view_mode is True
    @api.onchange("pos_self_order_view_mode")
    def _onchange_pos_self_order_view_mode(self):
        if not self.pos_self_order_view_mode:
            self.pos_self_order_ordering_mode = False

    @api.onchange("pos_self_order_ordering_mode")
    def _onchange_pos_self_order_ordering_mode(self):
        if self.pos_self_order_ordering_mode:
            self.pos_self_order_view_mode = True

    def preview_self_order_app(self):
        self.ensure_one()
        return self.pos_config_id.preview_self_order_app()

    def generate_qr_codes_page(self):
        if len(self.pos_config_id.floor_ids.table_ids) == 0:
            raise UserError(_("Before you can create QR codes, you need to create tables for the restaurant."))

        return self.env.ref("pos_self_order.report_self_order_qr_codes_page").report_action(
            [], data=self.pos_config_id._generate_qr_code()
        )
