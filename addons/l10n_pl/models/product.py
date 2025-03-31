from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pl_vat_gtu = fields.Selection(
        string='GTU Codes',
        selection=[
            ('GTU_01', 'GTU_01 - Alcoholic beverages'),
            ('GTU_02', 'GTU_02 - Goods referred to under Art. 103 sec 5aa'),
            ('GTU_03', 'GTU_03 - Fuel oil for excise duty, lubricating oils and other oils'),
            ('GTU_04', 'GTU_04 - Tobacco products, tobacco, e-liquid'),
            ('GTU_05', 'GTU_05 - Wastes'),
            ('GTU_06', 'GTU_06 - Electronic devices, their parts and materials'),
            ('GTU_07', 'GTU_07 - Vehicles and vehicle parts'),
            ('GTU_08', 'GTU_08 - Precious metals and base metals'),
            ('GTU_09', 'GTU_09 - Medicament and medical devices, medicinal products'),
            ('GTU_10', 'GTU_10 - Buildings, structures and land'),
            ('GTU_11', 'GTU_11 - Services related to the greenhouse gas emission allowance trading'),
            ('GTU_12', 'GTU_12 - Intangible services'),
            ('GTU_13', 'GTU_13 - Transport services and warehouse management services'),
        ],
        help='Codes for specific types of products, needed for VAT declaration'
    )
