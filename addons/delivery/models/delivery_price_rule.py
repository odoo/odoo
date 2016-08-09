# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
import odoo.addons.decimal_precision as dp


class PriceRule(models.Model):
    _name = "delivery.price.rule"
    _description = "Delivery Price Rules"
    _order = 'sequence, list_price'

    @api.depends('variable', 'operator', 'max_value', 'list_base_price', 'list_price', 'variable_factor')
    def _get_name(self):
        for rule in self:
            name = 'if %s %s %s then' % (rule.variable, rule.operator, rule.max_value)
            if rule.list_base_price and not rule.list_price:
                name = '%s fixed price %s' % (name, rule.list_base_price)
            elif rule.list_price and not rule.list_base_price:
                name = '%s %s times %s' % (name, rule.list_price, rule.variable_factor)
            else:
                name = '%s fixed price %s and %s times %s Extra' % (name, rule.list_base_price, rule.list_price, rule.variable_factor)
            rule.name = name

    name = fields.Char(compute='_get_name')
    sequence = fields.Integer(required=True, help="Gives the sequence order when calculating delivery carrier.", default=10)
    carrier_id = fields.Many2one('delivery.carrier', 'Carrier', required=True, ondelete='cascade')
    variable = fields.Selection([('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'), ('quantity', 'Quantity')], 'Variable', required=True, default='weight')
    operator = fields.Selection([('==', '='), ('<=', '<='), ('<', '<'), ('>=', '>='), ('>', '>')], 'Operator', required=True, default='<=')
    max_value = fields.Float('Maximum Value', required=True)
    variable_factor = fields.Selection([('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'), ('quantity', 'Quantity')], 'Variable Factor', required=True, default='weight')
    list_base_price = fields.Float(string='Sale Base Price', digits=dp.get_precision('Product Price'), required=True, default=0.0)
    list_price = fields.Float('Sale Price', digits=dp.get_precision('Product Price'), required=True, default=0.0)
    standard_price = fields.Float('Cost Price', digits=dp.get_precision('Product Price'), required=True, default=0.0)
