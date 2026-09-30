from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_my_tax_classification_code = fields.Char(
        string="Malaysian Customs Tariff Code",
        help="A unique identifier for classifying items for official declaration. It holds the Customs Tariff Code for physical goods or the Service Type Code for services.",
    )
