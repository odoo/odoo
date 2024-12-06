# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class BarcodeRulePart(models.Model):
    _inherit = 'barcode.rule.part'

    type = fields.Selection(
        selection_add=[
            ('weight', 'Weighted Product'),
            ('price', 'Priced Product'),
            ('discount', 'Discounted Product'),
            ('client', 'Client'),
            ('cashier', 'Cashier')
        ], ondelete={
            'weight': 'set default',
            'price': 'set default',
            'discount': 'set default',
            'client': 'set default',
            'cashier': 'set default',
        })
