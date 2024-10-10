# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class IapService(models.Model):
    _name = 'iap.service'
    _description = 'IAP Service'

    name = fields.Char(required=True)
    technical_name = fields.Char(readonly=True, required=True)
    description = fields.Char(required=True, translate=True)
    unit_name = fields.Char(required=True, translate=True)
    integer_balance = fields.Boolean(required=True)

    _unique_technical_name = models.Constraint(
        'UNIQUE(technical_name)',
        'Only one service can exist with a specific technical_name',
    )
