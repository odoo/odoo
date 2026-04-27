from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ae_tax_report_liabilities_account = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ae_tax_report_liabilities_account',
        string="Liabilities Account for Tax Report",
        readonly=False,
    )
    l10n_ae_tax_report_counterpart_account = fields.Many2one(
        comodel_name='account.account',
        related='company_id.l10n_ae_tax_report_counterpart_account',
        string="Tax Report Counter Part Account",
        readonly=False,
    )
