# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models, _


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_quotations = fields.Boolean(string='Quotations', help="Check this box if you send quotations to your customers rather than confirming orders straight away. "
                                                              "This will add specific action buttons to your dashboard.")
    use_invoices = fields.Boolean('Set Invoicing Target', help="Check this box to set an invoicing target for this Sales Team.")
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
    quotations_count = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Number of quotations to invoice', readonly=True)
    quotations_amount = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Amount of quotations to invoice', readonly=True)
    sales_to_invoice_count = fields.Integer(
        compute='_compute_sales_to_invoice',
        string='Number of sales to invoice', readonly=True)
    dashboard_graph_model = fields.Selection(selection_add=[
        ('sale.report', 'Sales'),
        ('account.invoice.report', 'Invoices'),
    ])

    def _compute_quotations_to_invoice(self):
        non_website_teams = self.filtered(lambda team: team.team_type != 'website')
        if non_website_teams:
            query = self.env['sale.order']._where_calc([
                ('team_id', 'in', non_website_teams.ids),
                ('state', 'in', ['draft', 'sent']),
            ])
            self.env['sale.order']._apply_ir_rules(query, 'read')
            _, where_clause, where_clause_args = query.get_sql()
            select_query = """
                SELECT team_id, count(*), sum(amount_total /
                    CASE COALESCE(currency_rate, 0)
                    WHEN 0 THEN 1.0
                    ELSE currency_rate
                    END
                ) as amount_total
                FROM sale_order
                WHERE %s
                GROUP BY team_id
            """ % where_clause
            self.env.cr.execute(select_query, where_clause_args)
            quotation_data = self.env.cr.dictfetchall()
            for datum in quotation_data:
                self.browse(datum['team_id']).quotations_amount = datum['amount_total']
                self.browse(datum['team_id']).quotations_count = datum['count']

    @api.multi
    def _compute_sales_to_invoice(self):
        sale_order_data = self.env['sale.order'].read_group([
            ('team_id', 'in', self.ids),
            ('order_line.qty_to_invoice', '>', 0),
        ], ['team_id'], ['team_id'])
        for datum in sale_order_data:
            self.browse(datum['team_id'][0]).invoiced = datum['team_id_count']

    @api.multi
    def _compute_invoiced(self):
        invoice_data = self.env['account.invoice'].read_group([
            ('state', 'in', ['open', 'in_payment', 'paid']),
            ('team_id', 'in', self.ids),
            ('date', '<=', date.today()),
            ('date', '>=', date.today().replace(day=1)),
            ('type', 'in', ['out_invoice', 'out_refund']),
        ], ['amount_untaxed_signed', 'team_id'], ['team_id'])
        for datum in invoice_data:
            self.browse(datum['team_id'][0]).invoiced = datum['amount_untaxed_signed']

    def _graph_date_column(self):
        if self.dashboard_graph_model == 'sale.report':
            return 'confirmation_date'
        elif self.dashboard_graph_model == 'account.invoice.report':
            return 'date'
        return super(CrmTeam, self)._graph_date_column()

    def _graph_y_query(self):
        if self.dashboard_graph_model == 'sale.report':
            return 'SUM(price_subtotal)'
        elif self.dashboard_graph_model == 'account.invoice.report':
            return 'SUM(price_total)'
        return super(CrmTeam, self)._graph_y_query()

    def _extra_sql_conditions(self):
        if self.dashboard_graph_model == 'sale.report':
            return "AND state in ('sale', 'done')"
        elif self.dashboard_graph_model == 'account.invoice.report':
            return "AND state in ('open', 'in_payment', 'paid')"
        return super(CrmTeam, self)._extra_sql_conditions()

    def _graph_title_and_key(self):
        if self.dashboard_graph_model == 'sale.report':
            return ['', _('Sales: Untaxed Total')] # no more title
        elif self.dashboard_graph_model == 'account.invoice.report':
            return ['', _('Invoices: Untaxed Total')]
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
            if not self.dashboard_graph_model:
                self.dashboard_graph_model = 'sale.report'
        else:
            self.use_quotations = False
            self.use_invoices = False
            self.dashboard_graph_model = 'sale.report'
        return super(CrmTeam, self)._onchange_team_type()

    @api.multi
    def update_invoiced_target(self, value):
        return self.write({'invoiced_target': round(float(value or 0))})
