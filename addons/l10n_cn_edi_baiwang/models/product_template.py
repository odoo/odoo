# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_tax_category_id = fields.Many2one(
        comodel_name='l10n_cn_edi.tax.category',
        string="Tax Category Code",
        help="19-digit official Golden Tax classification code (税收分类编码).",
        copy=False,
    )
