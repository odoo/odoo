# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time
from openerp.osv import fields, osv


class account_analytic_cost_ledger_journal_report(osv.osv_memory):
    _name = 'account.analytic.cost.ledger.journal.report'
    _description = 'Account Analytic Cost Ledger For Journal Report'

    _columns = {
        'date1': fields.date('Start of period', required=True),
        'date2': fields.date('End of period', required=True),
        'journal': fields.many2many('account.analytic.journal', 'ledger_journal_rel', 'ledger_id', 'journal_id', 'Journals'),
    }

    _defaults = {
        'date1': lambda *a: time.strftime('%Y-01-01'),
        'date2': lambda *a: time.strftime('%Y-%m-%d')
    }

    def check_report(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data = self.read(cr, uid, ids)[0]
        datas = {
            'ids': context.get('active_ids', []),
            'model': 'account.analytic.account',
            'form': data
        }

        datas['form']['active_ids'] = context.get('active_ids', False)
        return self.pool['report'].get_action(cr, uid, [], 'account.report_analyticcostledgerquantity', data=datas, context=context)
