from odoo import api, models


class PricerPosConfig(models.Model):
    _inherit = 'pos.config'

    @api.model
    def enable_pos_pricelists_demo(self):
        all_pos_configs = self.env['pos.config'].search([])
        for pos_config in all_pos_configs:
            pos_config.use_pricelist = True
