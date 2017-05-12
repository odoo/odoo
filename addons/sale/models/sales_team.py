# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_quotations = fields.Boolean('Quotations', default=True,
        help="Check this box to manage quotations in this sales team.")
    use_invoices = fields.Boolean('Invoices',
        help="Check this box to manage invoices in this sales team.")
    invoiced = fields.Integer(
        compute='_compute_invoiced',
        string='Invoiced This Month', readonly=True,
        help="Invoice revenue for the current month. This is the amount the sales "
                "team has invoiced this month. It is used to compute the progression ratio "
                "of the current and target revenue on the kanban view.")
    invoiced_target = fields.Integer(
        string='Invoice Target',
        help="Target of invoice revenue for the current month. This is the amount the sales "
             "team estimates to be able to invoice this month.")
    sales_to_invoice_amount = fields.Integer(
        compute='_compute_sales_to_invoice_amount',
        string='Amount of sales to invoice', readonly=True,
    )
    currency_id = fields.Many2one("res.currency", related='company_id.currency_id',
        string="Currency", readonly=True, required=True)

    @api.multi
    def _compute_sales_to_invoice_amount(self):
        amounts = self.env['sale.order'].read_group([
            ('team_id', 'in', self.ids),
            ('invoice_status', '=', 'to invoice'),
        ], ['amount_total', 'team_id'], ['team_id'])
        for rec in amounts:
            self.browse(rec['team_id'][0]).sales_to_invoice_amount = rec['amount_total']

    @api.multi
    def _compute_invoiced(self):
        for team in self:
            invoices = self.env['account.invoice'].search([
                ('state', 'in', ['open', 'paid']),
                ('team_id', '=', team.id),
                ('date', '<=', date.today()),
                ('date', '>=', date.today().replace(day=1)),
                ('type', 'in', ['out_invoice', 'out_refund']),
            ])
            team.invoiced = sum(invoices.mapped('amount_untaxed_signed'))

    @api.multi
    def update_invoiced_target(self, value):
        return self.write({'invoiced_target': round(float(value or 0))})

    @api.onchange('use_quotations')
    def _onchange_use_quotation(self):
        if self.use_quotations:
            self.use_invoices = True
