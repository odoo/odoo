# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, SUPERUSER_ID


class res_company(models.Model):
    _inherit = 'res.company'

    rule_type = fields.Selection([('not_synchronize', 'Do not synchronize'),
        ('invoice_and_refund', 'Synchronize invoices/bills')], string="Rule",
        help='Select the type to setup inter company rules in selected company.', default='not_synchronize')
    intercompany_user_id = fields.Many2one("res.users", string="Create as", default=SUPERUSER_ID, domain=["|", ["active", "=", True], ["id", "=", SUPERUSER_ID]],
        help="Responsible user for creation of documents triggered by intercompany rules.")
    intercompany_transaction_message = fields.Char(compute='_compute_intercompany_transaction_message')

    @api.depends('rule_type', 'name')
    def _compute_intercompany_transaction_message(self):
        for record in self:
            if record.rule_type == 'invoice_and_refund':
                record.intercompany_transaction_message = _(
                    "Generate a bill/invoice when a company confirms an invoice/bill for %s. "
                    "The new bill/invoice will be created in the first Purchase/Sales Journal of the Journals list view.",
                    record.name)
            else:
                record.intercompany_transaction_message = ''

    @api.model
    def _find_company_from_partner(self, partner_id):
        if not partner_id:
            return False
        company = self.sudo().search([('partner_id', 'parent_of', partner_id)], limit=1)
        return company or False
