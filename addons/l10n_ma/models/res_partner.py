# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_ma_ice = fields.Char(
        string='ICE',
        help="Company Common Identifier. If left empty, customs ICE 20727020 will be automatically applied to XML VAT report for foreign partners.",
    )
