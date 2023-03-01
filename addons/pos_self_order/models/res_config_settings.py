# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import split_every



class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_self_order_view_mode = fields.Boolean(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False)
    pos_self_order_image = fields.Image(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False, max_width=1920, max_height=1080)
    pos_self_order_image_name = fields.Char(
        compute="_compute_pos_module_pos_self_order", store=True, readonly=False)

    @api.depends("pos_config_id")
    def _compute_pos_module_pos_self_order(self):
        for res_config in self:
            if not res_config.pos_config_id.self_order_view_mode:
                res_config.update(
                    {
                        "pos_self_order_view_mode": False,
                        "pos_self_order_image": False,
                        "pos_self_order_image_name": False,
                    }
                )
            else:
                res_config.update(
                    {
                        "pos_self_order_view_mode": res_config.pos_config_id.self_order_view_mode,
                        "pos_self_order_image": res_config.pos_config_id.self_order_image,
                        "pos_self_order_image_name": res_config.pos_config_id.self_order_image_name,
                    }
                )

    def generate_qr_codes_page(self):
        """
        Generate the data needed to print the QR codes page
        """
        no_of_qr_codes_per_page = 16
        qr_codes_to_print = [
            {
                "id": 0,
                "url": f"{self.get_base_url()}/menu/{self.pos_config_id.id}",
            }
            for i in range(no_of_qr_codes_per_page)
        ]
        data = {
            "groups_of_tables": list(split_every(4, qr_codes_to_print, list)),
        }
        return self.env.ref("pos_self_order.report_self_order_qr_codes_page").report_action([], data=data)

    def preview_self_order_app(self):
        """
        This function calls the preview_self_order_app function of the pos.config model
        """
        self.ensure_one()
        return self.pos_config_id.preview_self_order_app()
