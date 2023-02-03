# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PriceRule(models.Model):
    _name = "delivery.price.rule"
    _description = "Delivery Price Rules"
    _order = 'sequence, list_price, id'

    @api.depends('variable', 'operator', 'max_value', 'list_base_price', 'list_price', 'variable_factor')
    def _compute_name(self):
        for rule in self:
            name = 'if %s %s %.02f then' % (rule.variable, rule.operator, rule.max_value)
            if rule.list_base_price and not rule.list_price:
                name = '%s fixed price %.02f' % (name, rule.list_base_price)
            elif rule.list_price and not rule.list_base_price:
                name = '%s %.02f times %s' % (name, rule.list_price, rule.variable_factor)
            else:
                name = '%s fixed price %.02f plus %.02f times %s' % (name, rule.list_base_price, rule.list_price, rule.variable_factor)
            rule.name = name

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer(required=True, default=10)
    carrier_id = fields.Many2one('delivery.carrier', 'Carrier', required=True, ondelete='cascade')

    variable = fields.Selection([('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'), ('quantity', 'Quantity')], required=True, default='weight')
    operator = fields.Selection([('==', '='), ('<=', '<='), ('<', '<'), ('>=', '>='), ('>', '>')], required=True, default='<=')
    max_value = fields.Float('Maximum Value', required=True)
    list_base_price = fields.Float(string='Sale Base Price', digits='Product Price', required=True, default=0.0)
    list_price = fields.Float('Sale Price', digits='Product Price', required=True, default=0.0)
    variable_factor = fields.Selection([('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'), ('quantity', 'Quantity')], 'Variable Factor', required=True, default='weight')
