# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, _


class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    l10n_br_move_id = fields.Many2one("account.move", help="Technical field that assigns this package to an invoice for Brazilian EDI.")
