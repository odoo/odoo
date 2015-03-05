import json
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from openerp import models, api, _, fields

class account_journal(models.Model):
    _inherit = "account.journal"

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_journal_dashboard_datas())

    @api.one
    def _kanban_dashboard_graph(self):
        self.kanban_dashboard_graph = json.dumps(self.get_graph_datas())

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    show_on_dashboard = fields.Boolean(string='Show journal on dashboard', help="Whether this journal should be displayed on the dashboard or not", default=False)

    @api.multi
    def get_graph_datas(self):
        data = []
        today = datetime.today()
        for i in range(0,30):
            today = today + timedelta(days=1)
            data.append({'name':today.strftime('%d %b'),'y':i*2, 'x':today.strftime('%d %B %Y')})
        return [{'values': data, 'color': '#ff7f0e', 'area': True, 'key': 'Value'}]

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