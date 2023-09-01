# -*- coding: utf-8 -*-

from odoo import models, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    @api.onchange("pos_self_order_kiosk")
    def _self_order_kiosk_change(self):
        super()._self_order_kiosk_change()

        for record in self:
            if record.pos_config_id.self_order_kiosk:
                if not record.pos_crm_team_id:
                    record.pos_crm_team_id = self.env.ref('pos_self_order_sale.pos_sales_team', raise_if_not_found=False)
