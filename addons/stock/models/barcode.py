# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[
        ('weight', 'Weighted Product'),
        ('location', 'Location'),
        ('lot', 'Lot'),
        ('package', 'Package')
    ], ondelete={
        'weight': 'set default',
        'location': 'set default',
        'lot': 'set default',
        'package': 'set default',
    })
