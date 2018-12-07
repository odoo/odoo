# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date

from odoo import api, fields, models, _


class CrmTeam(models.Model):
    _inherit = 'crm.team'

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


    def _compute_quotations_to_invoice(self):
        query = self.env['sale.order']._where_calc([
            ('team_id', 'in', self.ids),
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
        data_map = {datum['team_id'][0]: datum['team_id_count'] for datum in sale_order_data }
        for team in self:
            team.sales_to_invoice_count = data_map.get(team.id,0.0)

    @api.multi
    def _compute_invoiced(self):
        invoice_data = self.env['account.invoice'].read_group([
            ('state', 'in', ['open', 'in_payment', 'paid']),
            ('team_id', 'in', self.ids),
            ('date', '<=', date.today()),
            ('date', '>=', date.today().replace(day=1)),
            ('type', 'in', ['out_invoice', 'out_refund']),
        ], ['amount_untaxed_signed', 'team_id'], ['team_id'])
        data_map = { datum['team_id'][0]: datum['amount_untaxed_signed'] for datum in invoice_data}
        for team in self:
            team.invoiced = data_map.get(team.id,0.0)
    
    def _graph_get_model(self):
        if self._context.get('in_sales_app'):
            return 'sale.report'
        return super(CrmTeam,self)._graph_get_model()

    def _graph_date_column(self):
        if self._context.get('in_sales_app'):
            return 'confirmation_date'
        return super(CrmTeam,self)._graph_date_column()

    def _graph_y_query(self):
        if self._context.get('in_sales_app'):
            return 'SUM(price_subtotal)'
        return super(CrmTeam,self)._graph_y_query()

    def _extra_sql_conditions(self):
        if self._context.get('in_sales_app'):
            return "AND state in ('sale', 'done', 'pos_done')"
        return super(CrmTeam,self)._extra_sql_conditions()

    def _graph_title_and_key(self):
        if self._context.get('in_sales_app'):
            return ['', _('Sales: Untaxed Total')] # no more title
        return super(CrmTeam, self)._graph_title_and_key()

    def _compute_dashboard_button_name(self):
        super(CrmTeam,self)._compute_dashboard_button_name()
        if self._context.get('in_sales_app'):
            self.update({'dashboard_button_name': _("Sales Analysis")})

    def action_primary_channel_button(self):
        if self._context.get('in_sales_app'):
            return self.env.ref('sale.action_order_report_so_salesteam').read()[0]
        return super(CrmTeam, self).action_primary_channel_button()
            
    @api.multi
    def update_invoiced_target(self, value):
        return self.write({'invoiced_target': round(float(value or 0))})
