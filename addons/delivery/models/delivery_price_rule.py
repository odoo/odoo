# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import format_amount


VARIABLE_SELECTION = [
    ('weight', "Weight"),
    ('volume', "Volume"),
    ('wv', "Weight * Volume"),
    ('price', "Price"),
    ('quantity', "Quantity"),
]


class DeliveryPriceRule(models.Model):
    _name = 'delivery.price.rule'
    _description = "Delivery Price Rules"
    _order = 'sequence, list_price, id'

    @api.depends('variable', 'operator', 'max_value', 'list_base_price', 'list_price', 'variable_factor', 'currency_id')
    def _compute_name(self):
        for rule in self:
            name = 'if %s %s %.02f then' % (rule.variable, rule.operator, rule.max_value)
            if rule.currency_id:
                base_price = format_amount(self.env, rule.list_base_price, rule.currency_id)
                price = format_amount(self.env, rule.list_price, rule.currency_id)
            else:
                base_price = "%.2f" % rule.list_base_price
                price = "%.2f" % rule.list_price
            if rule.list_base_price and not rule.list_price:
                name = '%s fixed price %s' % (name, base_price)
            elif rule.list_price and not rule.list_base_price:
                name = '%s %s times %s' % (name, price, rule.variable_factor)
            else:
                name = '%s fixed price %s plus %s times %s' % (
                    name, base_price, price, rule.variable_factor
                )
            rule.name = name

    name = fields.Char(compute='_compute_name')
    sequence = fields.Integer(required=True, default=10)
    carrier_id = fields.Many2one('delivery.carrier', 'Carrier', required=True, index=True, ondelete='cascade')
    currency_id = fields.Many2one(related='carrier_id.currency_id')

    variable = fields.Selection(selection=VARIABLE_SELECTION, required=True, default='quantity')
    operator = fields.Selection([('==', '='), ('<=', '<='), ('<', '<'), ('>=', '>='), ('>', '>')], required=True, default='<=')
    max_value = fields.Float('Maximum Value', required=True)
    list_base_price = fields.Float(string='Sale Base Price', min_display_digits='Product Price', required=True, default=0.0)
    list_price = fields.Float('Sale Price', min_display_digits='Product Price', required=True, default=0.0)
    variable_factor = fields.Selection(
        selection=VARIABLE_SELECTION, string="Variable Factor", required=True, default='weight'
    )
