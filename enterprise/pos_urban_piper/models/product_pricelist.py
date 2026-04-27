from odoo import models, api


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    @api.model
    def write(self, vals):
        res = super().write(vals)
        for pricelist in self:
            urban_piper_configs = self.env['pos.config'].sudo().search([
                ('company_id', '=', pricelist.company_id.id),
                ('module_pos_urban_piper', '=', True),
                ('urbanpiper_pricelist_id', '=', pricelist.id),
            ])
            if urban_piper_configs:
                urban_piper_configs._reset_urbanpiper_product_linkages()
        return res
