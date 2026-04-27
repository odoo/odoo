from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_pe_type_of_existence = fields.Selection(
        [
            ('1', 'Merchandise'),
            ('2', 'Finished Products'),
            ('3', 'Raw Materials'),
            ('4', 'Containers'),
            ('5', 'Auxiliary Materials'),
            ('6', 'Supplies'),
            ('7', 'Spare Parts'),
            ('8', 'Packaging'),
            ('9', 'Subproducts'),
            ('10', 'Waste and Scrap'),
            ('91', 'Others 1'),
            ('92', 'Others 2'),
            ('93', 'Others 3'),
            ('94', 'Others 4'),
            ('95', 'Others 5'),
            ('96', 'Others 6'),
            ('97', 'Others 7'),
            ('98', 'Others 8'),
            ('99', 'Others'),
        ],
        string='Type of Existence',
        help="Select the type of existence according to SUNAT's Table 5 for inventory reporting.",
    )
