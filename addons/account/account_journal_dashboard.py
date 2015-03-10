import json
from datetime import datetime, date, timedelta

from babel.dates import format_datetime, format_date
from dateutil.relativedelta import relativedelta

from openerp import models, api, _, fields
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    @api.one
    def _kanban_dashboard_graph(self):
        if (self.type in ['sale', 'purchase']):
            self.kanban_dashboard_graph = json.dumps(self.get_bar_graph_datas())
        else:
            self.kanban_dashboard_graph = json.dumps(self.get_line_graph_datas())

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard', help="Whether this journal should be displayed on the dashboard or not", default=False)

    @api.multi
    def get_line_graph_datas(self):
        data = []
        today = datetime.today()
        for i in range(0,30):
            show_date = today + timedelta(days=-30+i)
            #get date in locale format
            name = format_date(show_date, 'd LLLL Y', locale=self._context.get('lang', 'en_US'))
            short_name = format_date(show_date, 'd MMM', locale=self._context.get('lang', 'en_US'))
            data.append({'x':short_name,'y':i*2, 'name':name})
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
        for invoice in self.env['account.invoice'].search([('journal_id','=',self.id),('state', '=', 'open')]):
            if invoice.date_due < (first_day_of_week + timedelta(days=-7)).strftime(DEFAULT_SERVER_DATE_FORMAT):
                data[0]['value'] += invoice.residual_signed
            elif invoice.date_due < first_day_of_week.strftime(DEFAULT_SERVER_DATE_FORMAT):
                data[1]['value'] += invoice.residual_signed
            elif invoice.date_due >= (first_day_of_week + timedelta(days=21)).strftime(DEFAULT_SERVER_DATE_FORMAT):
                data[5]['value'] += invoice.residual_signed
            elif invoice.date_due >= (first_day_of_week + timedelta(days=14)).strftime(DEFAULT_SERVER_DATE_FORMAT):
                data[4]['value'] += invoice.residual_signed
            elif invoice.date_due >= (first_day_of_week + timedelta(days=7)).strftime(DEFAULT_SERVER_DATE_FORMAT):
                data[3]['value'] += invoice.residual_signed
            else:
                data[2]['value'] += invoice.residual_signed
        return [{'values': data, 'title': title}]


    @api.multi
    def get_journal_dashboard_datas(self):
        number_to_reconcile = last_balance = 0
        ac_bnk_stmt = []
        number_draft = number_waiting = number_late = sum_draft = sum_waiting = sum_late = 0
        if self.type in ['bank', 'cash']:
            last_bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)], order="date desc", limit=1)
            last_balance = last_bank_stmt and last_bank_stmt[0].balance_end or 0 
            ac_bnk_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids),('state', '=', 'open')])
            for ac_bnk in ac_bnk_stmt:
                for line in ac_bnk.line_ids:
                    if not line.journal_entry_ids or not line.account_id:
                        number_to_reconcile += 1
        #TODO need to check if all invoices are in the same currency than the journal!!!!
        elif self.type in ['sale', 'purchase']:
            invoices = self.env['account.invoice'].search([('journal_id', 'in', self.ids), ('state', 'not in', ('paid', 'cancel'))])
            for invoice in invoices:
                if invoice.state in ['draft', 'proforma', 'proforma2']:
                    number_draft += 1
                    sum_draft += invoice.amount_total
                else:
                    number_waiting += 1
                    sum_waiting += invoice.residual
                    if invoice.date_due < fields.Date.today():
                        number_late += 1
                        sum_late += invoice.residual

        return {
            'number_to_reconcile': number_to_reconcile,
            'number_statement': len(ac_bnk_stmt),
            'last_balance': last_balance,
            'number_draft': number_draft,
            'number_waiting': number_waiting,
            'number_late': number_late,
            'sum_draft': sum_draft,
            'sum_waiting': sum_waiting,
            'sum_late': sum_late,
            'currency_id': self.currency and self.currency.id or self.company_id.currency_id.id,
            'show_import': True if self.type in ['bank', 'cash'] and len(ac_bnk_stmt) == 0 and last_balance == 0 else False,
        	}

    @api.multi
    def action_create_new(self):
        ctx = self._context.copy()
        model = 'account.invoice'
        if self.type == 'sale':
            if ctx.get('refund'):
                ctx.update({'default_type':'out_refund', 'type':'out_refund', 'journal_type': 'sale'})
            view_id = self.env.ref('account.invoice_form').id
        elif self.type == 'purchase':
            if ctx.get('refund'):
                ctx.update({'default_type': 'in_refund', 'type': 'in_refund', 'journal_type': 'purchase'})
            view_id = self.env.ref('account.invoice_supplier_form').id
        else:
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
    def action_open_reconcile(self):
        #search for bank_statement_ids with journal_id = self.ids
        bank_stmt = self.env['account.bank.statement'].search([('journal_id', 'in', self.ids)])
        return {
            'name': 'open reconciliation',
            'type': 'ir.actions.client',
            'tag': 'bank_statement_reconciliation_view',
            'context': {'statement_ids': bank_stmt.ids},
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

        _journal_invoice_type_map = {
            'sale': 'out_invoice',
            'purchase': 'in_invoice',
            'bank': 'bank',
            'cash': 'cash',
            'general': 'general',
            'opening': 'opening',
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
    def import_statement(self):
        """return action to import bank/cash statements"""
        model = 'account.bank.statement'
        if self.type == 'cash':
            model = 'account.cash.statement'
            return {
                'type': 'ir.actions.client',
                'tag': 'import',
                'params': {
                    'model': model,
                    'context': self._context,
                    }
                }
        else:
            action_name = 'action_account_bank_statement_import'
            ir_model_obj = self.pool['ir.model.data']
            model, action_id = ir_model_obj.get_object_reference(self._cr, self._uid, 'account_bank_statement_import', action_name)
            action = self.pool[model].read(self._cr, self._uid, action_id, context=self._context)
            return action