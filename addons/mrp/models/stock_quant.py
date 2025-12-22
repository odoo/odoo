from odoo import models, api, _
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.constrains('product_id')
    def _check_kits(self):
        if self.sudo().product_id.filtered("is_kits"):
            raise UserError(_('You should update the components quantity instead of directly updating the quantity of the kit product.'))

    def _should_bypass_product(self, product=False, location=False, reserved_quantity=0, lot_id=False, package_id=False, owner_id=False):
        return super()._should_bypass_product(product, location, reserved_quantity, lot_id, package_id, owner_id) or (product and product.is_kits)
