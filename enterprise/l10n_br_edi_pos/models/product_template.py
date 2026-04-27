# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_br_pos_warning = fields.Text("Brazilian POS Warning", compute="_compute_l10n_br_pos_warning")

    @api.depends("available_in_pos", "sale_ok", "taxes_id")
    def _compute_l10n_br_pos_warning(self):
        for product in self:
            product.l10n_br_pos_warning = False
            if product.available_in_pos and product.sale_ok and not all(product.taxes_id.mapped("price_include")):
                product.l10n_br_pos_warning = _("Products with price-excluded taxes will not be loaded in NFC-e Point of Sales.")
