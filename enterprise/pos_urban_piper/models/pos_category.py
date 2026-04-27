# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class PosCategory(models.Model):
    _inherit = 'pos.category'

    def write(self, vals):
        # In case of change in name or sequence of a POS category, we need to update it on the urban piper side
        if vals.get('sequence') or vals.get('name'):
            if linked_urbanpiper_status := self.env['product.urban.piper.status'].search([
                ('product_tmpl_id.pos_categ_ids', 'in', self.ids),
                ('is_product_linked', '=', True)
            ], limit=1):
                linked_urbanpiper_status.is_product_linked = False
        return super().write(vals)
