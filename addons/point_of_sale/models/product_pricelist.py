from odoo import models, _
from odoo.exceptions import UserError


class PosPayment(models.Model):
    _inherit = "product.pricelist"

    def write(self, vals):
        res = super().write(vals)
        if 'active' in vals and not vals['active'] and self.env['pos.config'].sudo().with_context(active_test=False).search_count([('pricelist_id', 'in', self.ids)]):
            raise UserError(_('You cannot archive a pricelist while it is being used as a default pricelist in a Point of Sale'))
        return res
