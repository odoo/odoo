# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_pk_edi_pct_code = fields.Char(
        string="PCT Code",
        help="PCT(Pakistan Customs Tariff) code is standardized code for classification of goods in Pakistan.",
    )
