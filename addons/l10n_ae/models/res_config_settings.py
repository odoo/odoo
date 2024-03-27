from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    enable_corporate_tax_report = fields.Boolean(
        string="Enable Corporate Tax Report",
        implied_group='l10n_ae.group_ae_corporate_tax_report',
        # help="Enable Corporate Tax Reports for UAE Localization",
    )
    tax_report_liabilities_account = fields.Many2one(
        comodel_name='account.account',
        string="Liabilities Account for Tax Report",
        readonly=False,
    )
    tax_report_counter_part_account = fields.Many2one(
        comodel_name='account.account',
        string="Tax Report Counter Part Account",
        readonly=False,
    )
