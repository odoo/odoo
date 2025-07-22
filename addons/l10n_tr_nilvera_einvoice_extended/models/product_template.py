from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_tr_ctsp_number = fields.Char(
        string="CTSP Number",
        compute="_compute_l10n_tr_ctsp_number",
        inverse="_set_l10n_tr_ctsp_number",
    )

    @api.depends("product_variant_ids.l10n_tr_ctsp_number")
    def _compute_l10n_tr_ctsp_number(self):
        self._compute_template_field_from_variant_field("l10n_tr_ctsp_number")

    def _set_l10n_tr_ctsp_number(self):
        self._set_product_variant_field("l10n_tr_ctsp_number")
