# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    trade_registry = fields.Char()
    l10n_cz_tax_office_id = fields.Many2one(
        string="Tax Office (CZ)",
        comodel_name='l10n_cz.tax_office',
    )
