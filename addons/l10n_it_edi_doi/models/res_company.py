# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.addons import l10n_it_edi, sale


class ResCompany(l10n_it_edi.ResCompany, sale.ResCompany):

    l10n_it_edi_doi_tax_id = fields.Many2one(
        comodel_name='account.tax',
        string="Declaration of Intent Tax",
    )

    l10n_it_edi_doi_fiscal_position_id = fields.Many2one(
        comodel_name='account.fiscal.position',
        string="Declaration of Intent Fiscal Position",
    )
