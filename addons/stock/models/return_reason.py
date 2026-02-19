# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReturnReason(models.Model):
    _name = 'return.reason'
    _description = "Reason to return delivered product(s)."
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
