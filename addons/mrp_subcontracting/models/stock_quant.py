# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_subcontract = fields.Boolean(store=False, search='_search_is_subcontract')

    def _search_is_subcontract(self, operator, value):
        if operator != 'in':
            return NotImplemented
        subcontracting_location_ids = self.env.companies.subcontracting_location_id.child_internal_location_ids.ids
        return [('location_id', operator, subcontracting_location_ids)]
