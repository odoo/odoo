# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_hu_product_code_type = fields.Selection(
        selection=[
            ('VTSZ', 'VTSZ - Customs Code'),
            ('SZJ', 'SZJ - Service Registry Code'),
            ('TESZOR', 'TESZOR - CPA 2.1 Code'),
            ('KN', 'KN - Combined Nomenclature Code'),
            ('AHK', 'AHK - e-TKO Excise Duty Code'),
            ('KT', 'KT - Environmental Product Code'),
            ('CSK', 'CSK - Packaging Catalogue Code'),
            ('EJ', 'EJ - Building Registry Number'),
            ('OTHER', 'Other'),
        ],
        string='Product Code Type',
        help='If your product has a code in a standard nomenclature, you can indicate which nomenclature here.',
    )
    l10n_hu_product_code = fields.Char(
        string='Product Code Value',
        help='If your product has a code in a standard nomenclature, you can indicate its code here.',
    )
