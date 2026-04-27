# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.constrains('quantity')
    def constrain_product_quantity(self):
        # Prevent negative quantity in any internal location
        domain = [
            ('product_id', '=', self.product_id.id),
            ('location_id.usage', 'in', ['internal', 'transit']),
            ('location_id.warehouse_id', '!=', False),
            ('location_id', '=', self.location_id.id),
            ('company_id.account_fiscal_country_id.code', '=', 'KE'),
        ]
        for location, quantity in self._read_group(domain, ['location_id'], ['quantity:sum']):
            if quantity < 0:
                raise ValidationError(_("You cannot end up with a negative stock quantity!"))
