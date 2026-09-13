from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_gr_edi_preferred_classification_ids = fields.One2many(
        comodel_name="l10n_gr_edi.preferred_classification",
        inverse_name="product_template_id",
        string="Preferred myDATA Classification",
    )
