# -*- coding: utf-8 -*-

from odoo import models, api
from odoo.addons import pos_self_order, pos_sale


class ResConfigSettings(pos_sale.ResConfigSettings, pos_self_order.ResConfigSettings):

    @api.onchange("pos_self_ordering_mode")
    def _onchange_pos_self_order_kiosk(self):
        super()._onchange_pos_self_order_kiosk()

        for record in self:
            if record.pos_config_id.self_ordering_mode == 'kiosk':
                if not record.pos_crm_team_id:
                    record.pos_crm_team_id = self.env.ref('pos_self_order_sale.pos_sales_team', raise_if_not_found=False)
