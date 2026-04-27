from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    barcodelookup_api_key = fields.Char(
        string='API key',
        config_parameter='product_barcodelookup.api_key',
        help='Barcode Lookup API Key for create product from barcode.',
    )
