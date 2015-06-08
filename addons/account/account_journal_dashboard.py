import json
from datetime import datetime, timedelta

from babel.dates import format_datetime, format_date

from openerp import models, api, _, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.misc import formatLang

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
        SQL_query = """SELECT a.date, a.balance_end 
                        FROM account_bank_statement AS a, 
                            (SELECT c.date, max(c.id) AS stmt_id 
                                FROM account_bank_statement AS c 
                                WHERE c.journal_id = %s 
                                    AND c.date > '%s' 
                                    AND c.date <= '%s' 
                                    GROUP BY date, id 
                                    ORDER BY date, id) AS b 
                        WHERE a.id = b.stmt_id;""" % (self.id, last_month.strftime(DEFAULT_SERVER_DATE_FORMAT), today.strftime(DEFAULT_SERVER_DATE_FORMAT))

        self.env.cr.execute(SQL_query)
        bank_stmt = self.env.cr.dictfetchall()

        last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids),('date', '<=', last_month.strftime(DEFAULT_SERVER_DATE_FORMAT))], order="date desc, id desc", limit=1)
        start_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0

        locale = self._context.get('lang', 'en_US')
        show_date = last_month
        #get date in locale format
        name = format_date(show_date, 'd LLLL Y', locale=locale)
        short_name = format_date(show_date, 'd MMM', locale=locale)
        data.append({'x':short_name,'y':start_balance, 'name':name})

        for stmt in bank_stmt:
            #fill the gap between last data and the new one
            number_day_to_add = (datetime.strptime(stmt.get('date'), DEFAULT_SERVER_DATE_FORMAT) - show_date).days
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

        return [{'values': data, 'color': '#ff7f0e', 'area': True}]

    @api.multi
    def get_bar_graph_datas(self):
        data = []
        title = _('Invoices owed to you')
        if self.type == 'purchase':
            title = _('Bills you need to pay')
        today = datetime.today()
        data.append({'label': _('Past'), 'value':0.0, 'color': '#ff0000'})
        day_of_week = int(format_datetime(today, 'e', locale=self._context.get('lang', 'en_US')))
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
                    label = str(start_week.day) + '-' +str(end_week.day)+ ' ' + format_date(end_week, 'MMM', locale=self._context.get('lang', 'en_US'))
                else:
                    label = format_date(start_week, 'd MMM', locale=self._context.get('lang', 'en_US'))+'-'+format_date(end_week, 'd MMM', locale=self._context.get('lang', 'en_US'))
            data.append({'label':label,'value':0.0, 'color': '#ff0000' if i<0 else '#ff7f0e'})

        # Build SQL query to find amount aggregated by week
        select_sql_clause = """SELECT sum(residual_signed) as total, min(date) as aggr_date from account_invoice where journal_id = %s and state = 'open'""" % (self.id)
        SQL_query = ''
        start_date = (first_day_of_week + timedelta(days=-7))
        for i in range(0,6):
            if i == 0:
                SQL_query += "("+select_sql_clause+" and date < '"+start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)+"')"
            elif i == 6:
                SQL_query += " UNION ALL ("+select_sql_clause+" and date >= '"+start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)+"')"
            else:
                next_date = start_date + timedelta(days=7)
                SQL_query += " UNION ALL ("+select_sql_clause+" and date >= '"+start_date.strftime(DEFAULT_SERVER_DATE_FORMAT)+"' and date < '"+next_date.strftime(DEFAULT_SERVER_DATE_FORMAT)+"')"
                start_date = next_date

        self.env.cr.execute(SQL_query)
        query_results = self.env.cr.dictfetchall()
        for index in range(0, len(query_results)):
            if query_results[index].get('aggr_date') != None:
                data[index]['value'] = query_results[index].get('total')
            else:
                data[index]['color'] = '#ffffff'

        return [{'values': data, 'title': title}]

    @api.multi
    def get_journal_dashboard_datas(self):
        number_to_reconcile = last_balance = account_sum = 0
        ac_bnk_stmt = []
        number_draft = number_waiting = number_late = sum_draft = sum_waiting = sum_late = 0
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc, id desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0
            ac_bnk_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids),('state', '=', 'open')])
            for ac_bnk in ac_bnk_stmt:
                for line in ac_bnk.line_ids:
                    if not line.journal_entry_ids:
                        number_to_reconcile += 1
            # optimization to read sum of balance from account_move_line
            SQL_query = """SELECT sum(balance) FROM account_move_line WHERE account_id in (%s, %s);""" % (self.default_debit_account_id.id, self.default_credit_account_id.id)
            self.env.cr.execute(SQL_query)
            query_results = self.env.cr.dictfetchall()
            if query_results and query_results[0].get('sum') != None:
                account_sum = query_results[0].get('sum')
        #TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            # optimization to find total and sum of invoice that are in draft, open state
            SQL_query = """SELECT state, count(id) AS count, sum(amount_total) AS total FROM account_invoice WHERE journal_id = %s AND state NOT IN ('paid', 'cancel') GROUP BY state;""" % (self.id)
            self.env.cr.execute(SQL_query)
            query_results = self.env.cr.dictfetchall()
            today = datetime.today()
            SQL_query = """SELECT count(id) AS count_late, sum(amount_total) AS total FROM account_invoice WHERE journal_id = %s AND date < '%s' AND state = 'open';""" % (self.id, today.strftime(DEFAULT_SERVER_DATE_FORMAT))
            self.env.cr.execute(SQL_query)
            late_query_results = self.env.cr.dictfetchall()
            for result in query_results:
                if result.get('state') in ['draft', 'proforma', 'proforma2']:
                    number_draft = result.get('count')
                    sum_draft = result.get('total')
                elif result.get('state') == 'open':
                    number_waiting = result.get('count')
                    sum_waiting = result.get('total')
            if late_query_results and late_query_results[0].get('count_late') != None:
                number_late = late_query_results[0].get('count_late')
                sum_late = late_query_results[0].get('total')

        return {
            'number_to_reconcile': number_to_reconcile,
            'account_balance': formatLang(self.env, account_sum, currency_obj=self.currency_id or self.company_id.currency_id),
            'last_balance': formatLang(self.env, last_balance, currency_obj=self.currency_id or self.company_id.currency_id),
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': formatLang(self.env, sum_draft, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_waiting': formatLang(self.env, sum_waiting, currency_obj=self.currency_id or self.company_id.currency_id),
            'sum_late': formatLang(self.env, sum_late, currency_obj=self.currency_id or self.company_id.currency_id),
            'currency_id': self.currency_id and self.currency_id.id or self.company_id.currency_id.id,
            'show_import': True if self.type in ['bank', 'cash'] and len(ac_bnk_stmt) == 0 and last_balance == 0 else False,
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
    def create_cash_bank(self):
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
                'context': {'statement_ids': bank_stmt.ids},
            }
        else:
            # Open reconciliation view for customers/suppliers
            action_context = {'show_mode_selector': False}
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
            'sale': 'out_invoice',
            'purchase': 'in_invoice',
            'bank': 'bank',
            'cash': 'cash',
            'general': 'general',
        }
        invoice_type = _journal_invoice_type_map[self.type]

        ctx = self._context.copy()
        ctx.update({
            'journal_type': self.type,
            'default_journal_id': self.id,
            'search_default_journal_id': self.id,
            'default_type': invoice_type,
            'type': invoice_type
        })
        ir_model_obj = self.pool['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account', action_name)
        action = self.pool[model].read(self._cr, self._uid, action_id, context=self._context)
        action['context'] = ctx
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
        action_rec = self.env['ir.model.data'].xmlid_to_object('account.action_account_payments')
        if action_rec:
            action = action_rec.read([])[0]
            action['context'] = ctx
            return action

    @api.multi
    def open_action_with_context(self):
        action_name = self.env.context.get('action_name', False)
        if not action_name:
            return False
        ctx = dict(self.env.context, default_journal_id=self.id)
        if ctx.get('search_default_journal', False):
            ctx.update(search_default_journal_id=self.id)
        ir_model_obj = self.pool['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account', action_name)
        action = self.pool[model].read(self._cr, self._uid, action_id, context=self._context)
        action['context'] = ctx
        if ctx.get('use_domain', False):
            action['domain'] = ['|', ('journal_id', '=', self.id), ('journal_id', '=', False)]
            action['name'] += ' for journal '+self.name
        return action

    @api.multi
    def import_statement(self):
        """return action to import bank/cash statements. This button should be called only on journals with type =='bank'"""
        model = 'account.bank.statement'
        action_name = 'action_account_bank_statement_import'
        ir_model_obj = self.pool['ir.model.data']
        model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account_bank_statement_import', action_name)
        action = self.pool[model].read(self._cr, self._uid, action_id, context=self._context)
        return action
