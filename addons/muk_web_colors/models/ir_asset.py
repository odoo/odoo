from odoo import models, fields, api


class IrAsset(models.Model):
    
    _inherit = 'ir.asset'
    
    # ----------------------------------------------------------
    # ORM
    # ----------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get('set_color_variables', False):
            for vals in vals_list:
                vals.pop('website_id', False)
        return super().create(vals_list)
