# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, _

from odoo.osv import expression
from odoo.tools import pycompat


class LunchProduct(models.Model):
    _inherit = 'lunch.product'

    # This field is used only for searching
    is_available_at = fields.Many2one('res.partner', 'Product Availability', compute='_compute_is_available_at', search='_search_is_available_at')

    def _compute_is_available_at(self):
        for product in self:
            product.is_available_at = False

    def _search_is_available_at(self, operator, value):
        if operator in ['=', '!=', 'ilike', 'not ilike'] and isinstance(value, pycompat.string_types):
            location_ids = self.env['res.partner'].search([('name', operator, value)]).ids

        if operator in ['='] and not value:
            if self.env.user.employee_ids and self.env.user.employee_ids[0].address_id:
                location_ids = self.env.user.employee_ids[0].address_id.ids

        if location_ids:
            suppliers = self.env['lunch.supplier'].search([('available_location_ids', 'in', location_ids)])
            product_ids = self.env['lunch.product'].search([('supplier', 'in', suppliers.ids)])
            return [('id', 'in', product_ids.ids)]

        return expression.TRUE_DOMAIN
