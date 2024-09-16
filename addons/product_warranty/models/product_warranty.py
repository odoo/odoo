# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductWarranty(models.Model):
    _name = "product.warranty"
    _description = "Warranty"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    duration = fields.Integer(default=1)
    duration_unit = fields.Selection(
        [('month', "Months"), ('year', "Years")],
        default='month',
        string="Unit")

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The warranty name must be unique.'),
        ('name_uniq', 'CHECK(duration_unit IS NOT NULL)', 'The duration unit should be set'),
    ]
