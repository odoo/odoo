# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PriceRule(models.Model):
    _inherit = "delivery.price.rule"

    @api.depends(
        'variable', 'operator', 'max_value', 'list_base_price', 'list_price', 'variable_factor'
    )
    def _compute_name(self):
        for rule in self:
            name = 'if %s %s %.02f then' % (rule.variable, rule.operator, rule.max_value)
            if rule.list_base_price and not rule.list_price:
                name = '%s fixed price %.02f' % (name, rule.list_base_price)
            elif rule.list_price and not rule.list_base_price:
                name = '%s %.02f times %s' % (name, rule.list_price, rule.variable_factor)
            else:
                name = '%s fixed price %.02f plus %.02f times %s' % (
                    name, rule.list_base_price, rule.list_price, rule.variable_factor
                )
            rule.name = name

    variable = fields.Selection(
        selection_add=[
            ('weight', 'Weight'),
            ('volume', 'Volume'),
            ('wv', 'Weight * Volume'),
            ('quantity', 'Quantity'),
        ],
        default='weight',
        ondelete={k: 'set default' for k in ['weight', 'volume', 'wv', 'quantity']},
    )
    variable_factor = fields.Selection(
        [
            ('weight', 'Weight'),
            ('volume', 'Volume'),
            ('wv', 'Weight * Volume'),
            ('price', 'Price'),
            ('quantity', 'Quantity'),
        ],
        'Variable Factor',
        required=True,
        default='weight',
    )
