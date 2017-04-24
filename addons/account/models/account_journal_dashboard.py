import json
from datetime import datetime, timedelta

from babel.dates import format_datetime, format_date

from odoo import models, api, _, fields
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools.misc import formatLang

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    @api.one
    def _kanban_dashboard_graph(self):
        if (self.type in ['sale', 'purchase']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        elif (self.type in ['cash', 'bank']):
            self.kanban_dashboard_graph = json.dumps(self.get_line_graph_datas())

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard', help="Whether this journal should be displayed on the dashboard or not", default=True)

    @api.multi
    def toggle_favorite(self):
        self.write({'show_on_dashboard': False if self.show_on_dashboard else True})
        return False

    @api.multi
    def get_line_graph_datas(self):
        data = []
        today = datetime.today()
        last_month = today + timedelta(days=-30)
        bank_stmt = []
        # Query to optimize loading of data for bank statement graphs
        # Return a list containing the latest bank statement balance per day for the
        # last 30 days for current journal
        query = """SELECT a.date, a.balance_end 
                        FROM account_bank_statement AS a, 
                            (SELECT c.date, max(c.id) AS stmt_id 
                                FROM account_bank_statement AS c 
                                WHERE c.journal_id = %s 
                                    AND c.date > %s 
                                    AND c.date <= %s 
                                    GROUP BY date, id 
                                    ORDER BY date, id) AS b 
                        WHERE a.id = b.stmt_id;"""

        self.env.cr.execute(query, (self.id, last_month, today))
        bank_stmt = self.env.cr.dictfetchall()

        last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids),('date', '<=', last_month.strftime(DF))], order="date desc, id desc", limit=1)
        start_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0

        locale = self._context.get('lang') or 'en_US'
        show_date = last_month
        #get date in locale format
        name = format_date(show_date, 'd LLLL Y', locale=locale)
        short_name = format_date(show_date, 'd MMM', locale=locale)
        data.append({'x':short_name,'y':start_balance, 'name':name})

        for stmt in bank_stmt:
            #fill the gap between last data and the new one
            number_day_to_add = (datetime.strptime(stmt.get('date'), DF) - show_date).days
            last_balance = data[len(data) - 1]['y']
            for day in range(0,number_day_to_add + 1):
                show_date = show_date + timedelta(days=1)
                #get date in locale format
                name = format_date(show_date, 'd LLLL Y', locale=locale)
                short_name = format_date(show_date, 'd MMM', locale=locale)
                data.append({'x': short_name, 'y':last_balance, 'name': name})
            #add new stmt value
            data[len(data) - 1]['y'] = stmt.get('balance_end')

        #continue the graph if the last statement isn't today
        if show_date != today:
            number_day_to_add = (today - show_date).days
            last_balance = data[len(data) - 1]['y']
            for day in range(0,number_day_to_add):
                show_date = show_date + timedelta(days=1)
                #get date in locale format
                name = format_date(show_date, 'd LLLL Y', locale=locale)
                short_name = format_date(show_date, 'd MMM', locale=locale)
                data.append({'x': short_name, 'y':last_balance, 'name': name})

        return [{'values': data, 'area': True}]

    @api.multi
    def get_bar_graph_datas(self):
        data = []
        today = datetime.strptime(fields.Date.context_today(self), DF)
        data.append({'label': _('Past'), 'value':0.0, 'type': 'past'})
        day_of_week = int(format_datetime(today, 'e', locale=self._context.get('lang') or 'en_US'))
        first_day_of_week = today + timedelta(days=-day_of_week+1)
        for i in range(-1,4):
            if i==0:
                label = _('This Week')
            elif i==3:
                label = _('Future')
            else:
                start_week = first_day_of_week + timedelta(days=i*7)
                end_week = start_week + timedelta(days=6)
                if start_week.month == end_week.month:
                    label = str(start_week.day) + '-' +str(end_week.day)+ ' ' + format_date(end_week, 'MMM', locale=self._context.get('lang') or 'en_US')
                else:
                    label = format_date(start_week, 'd MMM', locale=self._context.get('lang') or 'en_US')+'-'+format_date(end_week, 'd MMM', locale=self._context.get('lang') or 'en_US')
            data.append({'label':label,'value':0.0, 'type': 'past' if i<0 else 'future'})

        # Build SQL query to find amount aggregated by week
        select_sql_clause = """SELECT sum(residual_company_signed) as total, min(date) as aggr_date from account_invoice where journal_id = %(journal_id)s and state = 'open'"""
        query = ''
        start_date = (first_day_of_week + timedelta(days=-7))
        for i in range(0,6):
            if i == 0:
                query += "("+select_sql_clause+" and date < '"+start_date.strftime(DF)+"')"
            elif i == 5:
                query += " UNION ALL ("+select_sql_clause+" and date >= '"+start_date.strftime(DF)+"')"
            else:
                next_date = start_date + timedelta(days=7)
                query += " UNION ALL ("+select_sql_clause+" and date >= '"+start_date.strftime(DF)+"' and date < '"+next_date.strftime(DF)+"')"
                start_date = next_date

        self.env.cr.execute(query, {'journal_id':self.id})
        query_results = self.env.cr.dictfetchall()
        for index in range(0, len(query_results)):
            if query_results[index].get('aggr_date') != None:
                data[index]['value'] = query_results[index].get('total')

        return [{'values': data}]

    @api.multi
    def get_journal_dashboard_datas(self):
        currency = self.currency_id or self.company_id.currency_id
        number_to_reconcile = last_balance = account_sum = 0
        title = ''
        number_draft = number_waiting = number_late = sum_draft = sum_waiting = sum_late = 0
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            #Get the number of items to reconcile for that bank journal
            self.env.cr.execute("""SELECT COUNT(DISTINCT(line.id))
                            FROM account_bank_statement_line AS line
                            LEFT JOIN account_bank_statement AS st
                            ON line.statement_id = st.id
                            WHERE st.journal_id IN %s AND st.state = 'open'
                            AND not exists (select 1 from account_move_line aml where aml.statement_line_id = line.id)
                        """, (tuple(self.ids),))
            number_to_reconcile = self.env.cr.fetchone()[0]
            # optimization to read sum of balance from account_move_line
            account_ids = tuple(filter(None, [self.default_debit_account_id.id, self.default_credit_account_id.id]))
            if account_ids:
                amount_field = 'balance' if not self.currency_id else 'amount_currency'
                query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s;""" % (amount_field,)
                self.env.cr.execute(query, (account_ids,))
                query_results = self.env.cr.dictfetchall()
                if query_results and query_results[0].get('sum') != None:
                    account_sum = query_results[0].get('sum')
        #TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            title = _('Bills to pay') if self.type == 'purchase' else _('Invoices owed to you')
            # optimization to find total and sum of invoice that are in draft, open state
            query = """SELECT state, amount_total, currency_id AS currency FROM account_invoice WHERE journal_id = %s AND state NOT IN ('paid', 'cancel');"""
            self.env.cr.execute(query, (self.id,))
            query_results = self.env.cr.dictfetchall()
            today = datetime.today()
            query = """SELECT amount_total, currency_id AS currency FROM account_invoice WHERE journal_id = %s AND date < %s AND state = 'open';"""
            self.env.cr.execute(query, (self.id, today))
            late_query_results = self.env.cr.dictfetchall()
            sum_draft = 0.0
            number_draft = 0
            number_waiting = 0
            for result in query_results:
                cur = self.env['res.currency'].browse(result.get('currency'))
                if result.get('state') in ['draft', 'proforma', 'proforma2']:
                    number_draft += 1
                    sum_draft += cur.compute(result.get('amount_total'), currency)
                elif result.get('state') == 'open':
                    number_waiting += 1
                    sum_waiting += cur.compute(result.get('amount_total'), currency)
            sum_late = 0.0
            number_late = 0
            for result in late_query_results:
                cur = self.env['res.currency'].browse(result.get('currency'))
                number_late += 1
                sum_late += cur.compute(result.get('amount_total'), currency)

        return {
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, account_sum, currency_obj=self.currency_id or self.company_id.currency_id),
            'last_balance': formatLang(self.env, last_balance, currency_obj=self.currency_id or self.company_id.currency_id),
            'difference': (last_balance-account_sum) and formatLang(self.env, last_balance-account_sum, currency_obj=self.currency_id or self.company_id.currency_id) or False,
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, sum_draft or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_waiting': formatLang(self.env, sum_waiting or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_late': formatLang(self.env, sum_late or 0.0, currency_obj=self.currency_id or self.company_id.currency_id),
            'currency_id': self.currency_id and self.currency_id.id or self.company_id.currency_id.id,
            'bank_statements_source': self.bank_statements_source,
            'title': title, 
        }

    @api.multi
    def action_create_new(self):
        ctx = self._context.copy()
        model = 'account.invoice'
        if self.type == 'sale':
            ctx.update({'journal_type': self.type, 'default_type': 'out_invoice', 'type': 'out_invoice', 'default_journal_id': self.id})
            if ctx.get('refund'):
                ctx.update({'default_type':'out_refund', 'type':'out_refund'})
            view_id = self.env.ref('account.invoice_form').id
        elif self.type == 'purchase':
            ctx.update({'journal_type': self.type, 'default_type': 'in_invoice', 'type': 'in_invoice', 'default_journal_id': self.id})
            if ctx.get('refund'):
                ctx.update({'default_type': 'in_refund', 'type': 'in_refund'})
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
            ctx.update({'default_journal_id': self.id})
            view_id = self.env.ref('account.view_move_form').id
            model = 'account.move'
        return {
            'name': _('Create invoice/bill'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': model,
            'view_id': view_id,
            'context': ctx,
        }

    @api.multi
    def create_cash_statement(self):
        ctx = self._context.copy()
        ctx.update({'journal_id': self.id, 'default_journal_id': self.id, 'default_journal_type': 'cash'})
        return {
            'name': _('Create cash statement'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.bank.statement',
            'context': ctx,
        }

    @api.multi
    def action_open_reconcile(self):
        if self.type in ['bank', 'cash']:
            # Open reconciliation view for bank statements belonging to this journal
            bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)])
            return {
                'type': 'ir.actions.client',
                'tag': 'bank_statement_reconciliation_view',
                'context': {'statement_ids': bank_stmt.ids, 'company_ids': self.mapped('company_id').ids},
            }
        else:
            # Open reconciliation view for customers/suppliers
            action_context = {'show_mode_selector': False, 'company_ids': self.mapped('company_id').ids}
            if self.type == 'sale':
                action_context.update({'mode': 'customers'})
            elif self.type == 'purchase':
                action_context.update({'mode': 'suppliers'})
            return {
                'type': 'ir.actions.client',
                'tag': 'manual_reconciliation_view',
                'context': action_context,
            }

    @api.multi
    def open_action(self):
        """return action based on type for related journals"""
        action_name = self._context.get('action_name', False)
        if not action_name:
            if self.type == 'bank':
                action_name = 'action_bank_statement_tree'
            elif self.type == 'cash':
                action_name = 'action_view_bank_statement_tree'
            elif self.type == 'sale':
                action_name = 'action_invoice_tree1'
            elif self.type == 'purchase':
                action_name = 'action_invoice_tree2'
            else:
                action_name = 'action_move_journal_line'

        _journal_invoice_type_map = {
            ('sale', None): 'out_invoice',
            ('purchase', None): 'in_invoice',
            ('sale', 'refund'): 'out_refund',
            ('purchase', 'refund'): 'in_refund',
            ('bank', None): 'bank',
            ('cash', None): 'cash',
            ('general', None): 'general',
        }
        invoice_type = _journal_invoice_type_map[(self.type, self._context.get('invoice_type'))]

        ctx = self._context.copy()
        ctx.pop('group_by', None)
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'search_default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })

        [action] = self.env.ref('account.%s' % action_name).read()
        action['context'] = ctx
        action['domain'] = self._context.get('use_domain', [])
        if action_name in ['action_bank_statement_tree', 'action_view_bank_statement_tree']:
            action['views'] = False
            action['view_id'] = False
        return action

    @api.multi
    def open_spend_money(self):
        return self.open_payments_action('outbound')

    @api.multi
    def open_collect_money(self):
        return self.open_payments_action('inbound')

    @api.multi
    def open_transfer_money(self):
        return self.open_payments_action('transfer')

    @api.multi
    def open_payments_action(self, payment_type):
        ctx = self._context.copy()
        ctx.update({
            'default_payment_type': payment_type,
            'default_journal_id': self.id
        })
        ctx.pop('group_by', None)
        action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_account_payments')
        if action_rec:
            action = action_rec.read([])[0]
            action['context'] = ctx
            action['domain'] = [('journal_id','=',self.id),('payment_type','=',payment_type)]
            return action

    @api.multi
    def open_action_with_context(self):
        action_name = self.env.context.get('action_name', False)
        if not action_name:
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        if ctx.get('search_default_journal', False):
            ctx.update(search_default_journal_id=self.id)
        ctx.pop('group_by', None)
        ir_model_obj = self.env['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference('account', action_name)
        [action] = self.env[model].browse(action_id).read()
        action['context'] = ctx
        if ctx.get('use_domain', False):
            action['domain'] = ['|', ('journal_id', '=', self.id), ('journal_id', '=', False)]
            action['name'] += ' for journal ' + self.name
        return action

    @api.multi
    def create_bank_statement(self):
        """return action to create a bank statements. This button should be called only on journals with type =='bank'"""
        self.bank_statements_source = 'manual'
        action = self.env.ref('account.action_bank_statement_tree').read()[0]
        action.update({
            'views': [[False, 'form']],
            'context': "{'default_journal_id': " + str(self.id) + "}",
        })
        return action
