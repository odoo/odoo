# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.onchange('group_stock_production_lot')
    def _onchange_group_stock_production_lot(self):
        super()._onchange_group_stock_production_lot()
        if self.group_stock_production_lot:
            self.module_product_warranty = True
