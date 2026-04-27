# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    l10n_pe_fs_rubric_ids = fields.Many2many(
        comodel_name='l10n_pe_reports_lib.financial.rubric',
        string="Peruvian Financial statement rubric",
        domain=lambda self: ([('sector', '=', self.env.company.l10n_pe_financial_statement_type)])
    )


class L10nPeFinancialRubric(models.Model):
    _name = 'l10n_pe_reports_lib.financial.rubric'
    _description = 'Peruvian financial statement rubric'

    name = fields.Char("Code", required=True)
    sector = fields.Char("Sector", required=True)
    description = fields.Text("Description")
