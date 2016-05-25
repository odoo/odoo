# -*- coding: utf-8 -*-

from datetime import date

from odoo import api, fields, models, tools
from odoo.tools.float_utils import float_repr

class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_quotations = fields.Boolean('Quotations', help="Check this box to manage quotations in this sales team.", default=True)
    use_invoices = fields.Boolean('Invoices', help="Check this box to manage invoices in this sales team.")
    invoiced = fields.Integer(compute='_compute_invoiced', readonly=True, string='Invoiced This Month',
        help="Invoice revenue for the current month. This is the amount the sales "
                "team has invoiced this month. It is used to compute the progression ratio "
                "of the current and target revenue on the kanban view.")
    invoiced_target = fields.Integer(string='Invoice Target',
        help="Target of invoice revenue for the current month. This is the amount the sales "
                "team estimates to be able to invoice this month.")
    sales_to_invoice_amount = fields.Integer(compute='_compute_sales_to_invoice_amount', readonly=True, string='Amount of sales to invoice')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string="Currency", readonly=True, required=True)


    def _compute_sales_to_invoice_amount(self):
        domain = [
            ('team_id', 'in', self.ids),
            ('invoice_status', '=', 'to invoice'),
        ]
        amounts = self.env['sale.order'].read_group(domain, ['amount_total', 'team_id'], ['team_id'])
        for rec in amounts:
            self.browse(rec['team_id'][0]).sales_to_invoice_amount = rec['amount_total']
    
    def _compute_invoiced(self):
        # Cannot use read_group because amount_untaxed_signed is an unstored computed field.
        for team in self:
            domain = [
                ('state', 'in', ['open', 'paid']),
                ('team_id', '=', team.id),
                ('date', '<=', date.today()),
                ('date', '>=', date.today().replace(day=1))
            ]
            invoices = self.env['account.invoice'].search(domain)
            team.invoiced = sum([inv.amount_untaxed_signed for inv in invoices])

    @api.multi
    def update_invoiced_target(self, value):
        self.ensure_one()
        return self.write({'invoiced_target': round(float(value or 0))})
