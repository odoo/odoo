from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ae_tax_report_liabilities_account = fields.Many2one(comodel_name='account.account', string="Liabilities Account for Tax Report")
    l10n_ae_tax_report_counterpart_account = fields.Many2one(comodel_name='account.account', string="Tax Report Counter Part Account")
