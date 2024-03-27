from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_corporate_tax_report = fields.Boolean(string="Enable Corporate Tax Report", default=False)
    tax_report_liabilities_account = fields.Many2one(comodel_name='account.account', string="Liabilities Account for Tax Report")
    tax_report_counter_part_account = fields.Many2one(comodel_name='account.account', string="Tax Report Counter Part Account")
