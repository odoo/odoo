from odoo import fields, models


class BarcodeRulePart(models.Model):
    _inherit = 'barcode.rule.part'

    type = fields.Selection(
        selection_add=[
            ('location', 'Location'),
            ('location_dest', 'Destination location'),
            ('lot', 'Lot number'),
            ('package', 'Package'),
            ('use_date', 'Best before Date'),
            ('expiration_date', 'Expiration Date'),
            ('package_type', 'Package Type'),
            ('pack_date', 'Pack Date'),
        ], ondelete={
            'location': 'set default',
            'location_dest': 'set default',
            'lot': 'set default',
            'package': 'set default',
            'use_date': 'set default',
            'expiration_date': 'set default',
            'package_type': 'set default',
            'pack_date': 'set default',
        })
