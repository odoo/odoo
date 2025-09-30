# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    is_subcontract = fields.Boolean(store=False, search='_search_is_subcontract')

    def _search_is_subcontract(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError(_('Operation not supported'))

        return [('location_id.is_subcontracting_location', operator, value)]

    def _should_bypass_product(self, product=False, location=False, reserved_quantity=0, lot_id=False, package_id=False, owner_id=False):
        return super()._should_bypass_product(product, location, reserved_quantity, lot_id, package_id, owner_id) or (location and location.is_subcontracting_location)
