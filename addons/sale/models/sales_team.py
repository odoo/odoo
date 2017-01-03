# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models, _


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_quotations = fields.Boolean(string='Quotations', help="Check this box to manage quotations in this sales channel.")
    use_invoices = fields.Boolean('Set Invoicing Target', help="Check this box to set an invoicing target for this sales channel.")
    invoiced = fields.Integer(
        compute='_compute_invoiced',
        string='Invoiced This Month', readonly=True,
        help="Invoice revenue for the current month. This is the amount the sales "
                "channel has invoiced this month. It is used to compute the progression ratio "
                "of the current and target revenue on the kanban view.")
    invoiced_target = fields.Integer(
        string='Invoicing Target',
        help="Target of invoice revenue for the current month. This is the amount the sales "
             "channel estimates to be able to invoice this month.")
    quotations_to_invoice_count = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Number of quotations to invoice', readonly=True)
    quotations_to_invoice_amount = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Amount of quotations to invoice', readonly=True)
    sales_to_invoice_count = fields.Integer(
        compute='_compute_sales_to_invoice',
        string='Number of sales to invoice', readonly=True)
    dashboard_graph_model = fields.Selection(selection_add=[
        ('sales', 'Sales'),
        ('invoices', 'Invoices'),
    ])

    def _compute_quotations_to_invoice(self):
        amounts = self.env['sale.report'].read_group([
            ('team_id', 'in', self.filtered(lambda team: team.team_type != 'website').ids),
            ('state', 'in', ['draft', 'sent']),
        ], ['price_total', 'team_id', 'name'], ['team_id', 'name'], lazy=False)
        for rec in amounts:
            self.browse(rec['team_id'][0]).quotations_to_invoice_amount += rec['price_total']
            self.browse(rec['team_id'][0]).quotations_to_invoice_count += 1

    @api.multi
    def _compute_sales_to_invoice(self):
        amounts = self.env['sale.report'].read_group([
            ('team_id', 'in', self.ids),
            ('qty_to_invoice', '>', 0),
        ], ['team_id', 'name'], ['team_id', 'name'], lazy=False)
        for rec in amounts:
            self.browse(rec['team_id'][0]).sales_to_invoice_count += 1

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

    def _graph_date_column(self):
        if self.dashboard_graph_model in ['sales', 'invoices']:
            return 'date'
        return super(CrmTeam, self)._graph_date_column()

    def _graph_y_query(self):
        if self.dashboard_graph_model == 'sales':
            return 'SUM(price_subtotal)'
        elif self.dashboard_graph_model == 'invoices':
            return 'SUM(price_total)'
        return super(CrmTeam, self)._graph_y_query()

    def _graph_sql_table(self):
        if self.dashboard_graph_model == 'sales':
            return 'sale_report'
        elif self.dashboard_graph_model == 'invoices':
            return 'account_invoice_report'
        return super(CrmTeam, self)._graph_sql_table()

    def _extra_sql_conditions(self):
        if self.dashboard_graph_model == 'sales':
            return "AND state in ('sale', 'done')"
        elif self.dashboard_graph_model == 'invoices':
            return "AND state = 'paid'"
        return super(CrmTeam, self)._extra_sql_conditions()

    def _graph_title_and_key(self):
        if self.dashboard_graph_model == 'sales':
            return [_('Sales'), _('Untaxed Total')]
        elif self.dashboard_graph_model == 'invoices':
            return [_('Invoices'), _('Untaxed Total')]
        return super(CrmTeam, self)._graph_title_and_key()

    def _compute_dashboard_button_name(self):
        quotation_teams = self.filtered('use_quotations')
        quotation_teams.update({'dashboard_button_name': _("Quotations")})
        (self - quotation_teams).update({'dashboard_button_name': _("Sales Orders")})

    def action_primary_channel_button(self):
        if hasattr(self, 'use_opportunities') and self.use_opportunities:
            return super(CrmTeam, self).action_primary_channel_button()
        elif self.use_quotations:
            action = self.env.ref('sale.action_quotations_salesteams').read()[0]
            action['context'] = {'search_default_team_id': self.id}
            return action
        else:
            action = self.env.ref('sale.action_orders_salesteams').read()[0]
            action['context'] = {'search_default_team_id': self.id}
            return action

    @api.onchange('team_type')
    def _onchange_team_type(self):
        if self.team_type == 'sales':
            self.use_quotations = True
            self.use_invoices = True
            # do not override dashboard_graph_model 'pipeline' if crm is installed
            if not self.dashboard_graph_model:
                self.dashboard_graph_model = 'sales'
        else:
            self.use_quotations = False
            self.use_invoices = False
            self.dashboard_graph_model = 'sales'
        return super(CrmTeam, self)._onchange_team_type()

    @api.multi
    def update_invoiced_target(self, value):
        return self.write({'invoiced_target': round(float(value or 0))})
