# -*- coding: utf-8 -*-
from odoo.addons import barcodes
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class BarcodeRule(models.Model, barcodes.BarcodeRule):

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
