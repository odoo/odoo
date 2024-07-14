# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rule_type = fields.Selection(related='company_id.rule_type', readonly=False)
    intercompany_user_id = fields.Many2one(related='company_id.intercompany_user_id', readonly=False, required=True)
    rules_company_id = fields.Many2one(related='company_id', string='Select Company', readonly=True)
    intercompany_transaction_message = fields.Char(compute='_compute_intercompany_transaction_message')

    @api.depends('rule_type', 'company_id')
    def _compute_intercompany_transaction_message(self):
        for record in self:
            if record.rule_type == 'invoice_and_refund':
                record.intercompany_transaction_message = _(
                    "Generate a bill/invoice when a company confirms an invoice/bill for %s. "
                    "The new bill/invoice will be created in the first Purchase/Sales Journal of the Journals list view.",
                    record.company_id.name)
            else:
                record.intercompany_transaction_message = ''
