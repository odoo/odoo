# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ReturnReason(models.Model):
    _name = 'return.reason'
    _description = "Reason to return a ordered products."
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
