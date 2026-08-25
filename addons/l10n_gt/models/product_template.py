# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_gt_agricultural_product = fields.Boolean(
        string="Agricultural Product",
        help="Agricultural products are withheld at the higher VAT rate when the retention agent is an exporter.",
    )
