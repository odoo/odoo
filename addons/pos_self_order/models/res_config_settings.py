# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_order_view_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_table_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_kiosk_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False
    )
    pos_self_order_pay_after = fields.Selection(
        [("each", "Each Order"), ("meal", "Meal")],
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
            if not res_config.pos_config_id.self_order_view_mode and not res_config.pos_config_id.self_order_kiosk_mode:
                res_config.update(
                    {
                        "pos_self_order_view_mode": False,
                        "pos_self_order_table_mode": False,
                        "pos_self_order_kiosk_mode": False,
                        "pos_self_order_pay_after": "each",
                        "pos_self_order_image": False,
                        "pos_self_order_image_name": False,
                    }
                )
            else:
                res_config.update(
                    {
                        "pos_self_order_view_mode": res_config.pos_config_id.self_order_view_mode,
                        "pos_self_order_table_mode": res_config.pos_config_id.self_order_table_mode,
                        "pos_self_order_kiosk_mode": res_config.pos_config_id.self_order_kiosk_mode,
                        "pos_self_order_pay_after": res_config.pos_config_id.self_order_pay_after,
                        "pos_self_order_image": res_config.pos_config_id.self_order_image,
                        "pos_self_order_image_name": res_config.pos_config_id.self_order_image_name,
                    }
                )

    # self_order_table_mode is only available if self_order_view_mode is True
    @api.onchange("pos_self_order_view_mode")
    def _onchange_pos_self_order_view_mode(self):
        if not self.pos_self_order_view_mode:
            self.pos_self_order_table_mode = False

    @api.onchange("pos_self_order_table_mode")
    def _onchange_pos_self_order_table_mode(self):
        if self.pos_self_order_table_mode:
            self.pos_self_order_view_mode = True

    @api.onchange("pos_self_order_kiosk_mode")
    def _onchange_pos_self_order_kiosk(self):
        """
        Enabling kiosk mode will disable table mode.
        (if a pos is configured as kiosk, there is no reason to have it be a
        self-order pos too)
        here we take care of the situation where we have first set the
        pos as table_mode and then decided to set it as kiosk_mode.
        The reverse situation, where we first set the pos as kiosk_mode
        and then set it as table_mode, should be impossible, as enabling
        kiosk mode will hide most of the other settings, including self_order_table_mode
        """
        for pos_config in self:
            if pos_config.pos_self_order_kiosk_mode:
                pos_config.pos_self_order_table_mode = False
                pos_config.pos_self_order_view_mode = False
                pos_config.pos_self_order_pay_after = "each"

    def generate_qr_codes_page(self):
        """
        Generate the data needed to print the QR codes page
        """
        return self.env.ref("pos_self_order.report_self_order_qr_codes_page").report_action(
            [], data=self.pos_config_id._generate_data_for_qr_codes_page(cols=3)
        )

    def preview_self_order_app(self):
        self.ensure_one()
        return self.pos_config_id.preview_self_order_app()
