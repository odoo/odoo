# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class StockPackageType(models.Model):
    _inherit = "stock.package.type"

    l10n_br_brand = fields.Char("Brand", help="Brazil: brand of the packaging.")
