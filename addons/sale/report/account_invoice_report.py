# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    team_id = fields.Many2one(comodel_name='crm.team', string="Sales Team")
    source_id = fields.Many2one(comodel_name='utm.source', string="Source", readonly=True)

    @classmethod
    def setup(cls):
        super().setup()
        cls._depends['account.move'] = cls._depends.get('account.move', []) + ['source_id']

    def _select(self) -> SQL:
        return SQL("%s, move.source_id, move.team_id as team_id", super()._select())
