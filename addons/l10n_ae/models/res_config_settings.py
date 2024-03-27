from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_corporate_tax_report = fields.Boolean(
        related='company_id.enable_corporate_tax_report',
        readonly=False,
        stored=True,
        help="Enable Corporate Tax Reports for UAE Localization",
        implied_group='l10n_ae.group_ae_corporate_tax_report',
    )
    tax_report_liabilities_account = fields.Many2one(
        comodel_name='account.account',
        related='company_id.tax_report_liabilities_account',
        stored=True,
        readonly=False,
    )
    tax_report_counter_part_account = fields.Many2one(
        comodel_name='account.account',
        related='company_id.tax_report_counter_part_account',
        stored=True,
        readonly=False,
    )
