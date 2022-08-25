# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    use_quotations = fields.Boolean(string='Quotations', help="Check this box if you send quotations to your customers rather than confirming orders straight away.")
    invoiced = fields.Float(
        compute='_compute_invoiced',
        string='Invoiced This Month', readonly=True,
        help="Invoice revenue for the current month. This is the amount the sales "
                "channel has invoiced this month. It is used to compute the progression ratio "
                "of the current and target revenue on the kanban view.")
    invoiced_target = fields.Float(
        string='Invoicing Target',
        help="Revenue target for the current month (untaxed total of confirmed invoices).")
    quotations_count = fields.Integer(
        compute='_compute_quotations_to_invoice',
        string='Number of quotations to invoice', readonly=True)
    quotations_amount = fields.Float(
        compute='_compute_quotations_to_invoice',
        string='Amount of quotations to invoice', readonly=True)
    sales_to_invoice_count = fields.Integer(
        compute='_compute_sales_to_invoice',
        string='Number of sales to invoice', readonly=True)
    sale_order_count = fields.Integer(compute='_compute_sale_order_count', string='# Sale Orders')

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
        teams = self.browse()
        for datum in quotation_data:
            team = self.browse(datum['team_id'])
            team.quotations_amount = datum['amount_total']
            team.quotations_count = datum['count']
            teams |= team
        remaining = (self - teams)
        remaining.quotations_amount = 0
        remaining.quotations_count = 0

    def _compute_sales_to_invoice(self):
        sale_order_data = self.env['sale.order']._read_group([
            ('team_id', 'in', self.ids),
            ('invoice_status','=','to invoice'),
        ], ['team_id'], ['team_id'])
        data_map = {datum['team_id'][0]: datum['team_id_count'] for datum in sale_order_data}
        for team in self:
            team.sales_to_invoice_count = data_map.get(team.id,0.0)

    def _compute_invoiced(self):
        if not self:
            return

        query = '''
            SELECT
                move.team_id AS team_id,
                SUM(move.amount_untaxed_signed) AS amount_untaxed_signed
            FROM account_move move
            WHERE move.move_type IN ('out_invoice', 'out_refund', 'out_receipt')
            AND move.payment_state IN ('in_payment', 'paid', 'reversed')
            AND move.state = 'posted'
            AND move.team_id IN %s
            AND move.date BETWEEN %s AND %s
            GROUP BY move.team_id
        '''
        today = fields.Date.today()
        params = [tuple(self.ids), fields.Date.to_string(today.replace(day=1)), fields.Date.to_string(today)]
        self._cr.execute(query, params)

        data_map = dict((v[0], v[1]) for v in self._cr.fetchall())
        for team in self:
            team.invoiced = data_map.get(team.id, 0.0)

    def _compute_sale_order_count(self):
        data_map = {}
        if self.ids:
            sale_order_data = self.env['sale.order']._read_group([
                ('team_id', 'in', self.ids),
                ('state', '!=', 'cancel'),
            ], ['team_id'], ['team_id'])
            data_map = {datum['team_id'][0]: datum['team_id_count'] for datum in sale_order_data}
        for team in self:
            team.sale_order_count = data_map.get(team.id, 0)

    def _in_sale_scope(self):
        return self.env.context.get('in_sales_app')

    def _graph_get_model(self):
        if self._in_sale_scope():
            return 'sale.report'
        return super()._graph_get_model()

    def _graph_date_column(self):
        if self._in_sale_scope():
            return 'date'
        return super()._graph_date_column()

    def _graph_get_table(self, GraphModel):
        if self._in_sale_scope():
            # For a team not shared between company, we make sure the amounts are expressed
            # in the currency of the team company and not converted to the current company currency,
            # as the amounts of the sale report are converted in the currency
            # of the current company (for multi-company reporting, see #83550)
            GraphModel = GraphModel.with_company(self.company_id)
            return f"({GraphModel._table_query}) AS {GraphModel._table}"
        return super()._graph_get_table(GraphModel)

    def _graph_y_query(self):
        if self._in_sale_scope():
            return 'SUM(price_subtotal)'
        return super()._graph_y_query()

    def _extra_sql_conditions(self):
        if self._in_sale_scope():
            return "AND state in ('sale', 'done', 'pos_done')"
        return super()._extra_sql_conditions()

    def _graph_title_and_key(self):
        if self._in_sale_scope():
            return ['', _('Sales: Untaxed Total')] # no more title
        return super()._graph_title_and_key()

    def _compute_dashboard_button_name(self):
        super(CrmTeam,self)._compute_dashboard_button_name()
        if self._in_sale_scope():
            self.dashboard_button_name = _("Sales Analysis")

    def action_primary_channel_button(self):
        if self._in_sale_scope():
            return self.env["ir.actions.actions"]._for_xml_id("sale.action_order_report_so_salesteam")
        return super().action_primary_channel_button()

    def update_invoiced_target(self, value):
        return self.write({'invoiced_target': round(float(value or 0))})

    @api.ondelete(at_uninstall=False)
    def _unlink_except_used_for_sales(self):
        """ If more than 5 active SOs, we consider this team to be actively used.
        5 is some random guess based on "user testing", aka more than testing
        CRM feature and less than use it in real life use cases. """
        SO_COUNT_TRIGGER = 5
        for team in self:
            if team.sale_order_count >= SO_COUNT_TRIGGER:
                raise UserError(
                    _('Team %(team_name)s has %(sale_order_count)s active sale orders. Consider canceling them or archiving the team instead.',
                      team_name=team.name,
                      sale_order_count=team.sale_order_count
                      ))
