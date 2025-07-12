# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_subcontract = fields.Boolean(store=False, search='_search_is_subcontract')

    def _search_is_subcontract(self, operator, value):
        if operator not in ('=', '!='):
            return NotImplemented
        subcontracting_location_ids = self.env.companies.subcontracting_location_id.ids
        return [('location_id', 'in' if operator == '=' and value or operator == '!=' and not value else 'not in', subcontracting_location_ids)]
