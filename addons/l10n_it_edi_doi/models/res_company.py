# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_it_edi_doi_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Declaration of Intent Tax",
    )

    l10n_it_edi_doi_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Declaration of Intent Fiscal Position",
    )
