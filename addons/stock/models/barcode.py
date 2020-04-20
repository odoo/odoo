# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BarcodeRule(models.Model):
    _inherit = 'barcode.rule'

    type = fields.Selection(selection_add=[
        ('weight', 'Weighted Product'),
        ('location', 'Location'),
        ('lot', 'Lot'),
        ('package', 'Package'),
        ('qty_done', 'Quantity'),
        ('use_date', 'Best before Date'),
        ('expiration_date', 'Expiration Date'),
        ('packaging_date', 'Packaging Date')
    ], ondelete={
        'weight': 'set default',
        'location': 'set default',
        'lot': 'set default',
        'package': 'set default',
        'qty_done': 'set default',
        'use_date': 'set default',
        'expiration_date': 'set default',
        'packaging_date': 'set default',
    })
