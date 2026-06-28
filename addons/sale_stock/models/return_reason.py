# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReturnReason(models.Model):
    _name = "return.reason"
    _description = "Return Reason"
    _order = "sequence"

    name = fields.Char(string="Reason", required=True, translate=True)
    sequence = fields.Integer(default=10)
