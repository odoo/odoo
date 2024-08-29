from odoo import models, api, _
from odoo.addons import stock
from odoo.exceptions import UserError


class StockQuant(models.Model, stock.StockQuant):

    @api.constrains('product_id')
    def _check_kits(self):
        if self.sudo().product_id.filtered("is_kits"):
            raise UserError(_('You should update the components quantity instead of directly updating the quantity of the kit product.'))
