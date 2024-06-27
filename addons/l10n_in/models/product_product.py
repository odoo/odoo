from odoo import api, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('type')
    def _onchange_type(self):
        if self.env['account.move.line'].sudo().search_count([
            ('product_id', '=', self.id), ('parent_state', '=', 'posted')
        ]):
            raise UserError(_("You cannot change the product type because there are posted accounting moves associated with this product."))
        return super()._onchange_type()
