# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    team_id = fields.Many2one(comodel_name="crm.team", string="Sales Team")
    source_id = fields.Many2one(comodel_name="utm.source", string="Source", readonly=True)

    def _select_list(self, table):
        return super()._select_list(table) + [
            table.move_id.team_id,
            table.move_id.source_id,
        ]
