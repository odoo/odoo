# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

from odoo.addons.account.report.account_invoice_report import related_sql


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    team_id = fields.Many2one(comodel_name="crm.team", string="Sales Team", **related_sql('move_id.team_id'))
    source_id = fields.Many2one(comodel_name="utm.source", string="Source", **related_sql('move_id.source_id'))
