# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_subcontract = fields.Boolean(store=False, search='_search_is_subcontract')

    def _search_is_subcontract(self, operator, value):
        if operator != 'in':
            return NotImplemented
        return [('location_id.is_subcontracting_location', 'in', value)]
