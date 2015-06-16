# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class account_crossovered_analytic(osv.osv_memory):
    _name = "account.crossovered.analytic"
    _description = "Print Crossovered Analytic"
    _columns = {
        'date1': fields.date('Start Date', required=True),
        'date2': fields.date('End Date', required=True),
        'journal_ids': fields.many2many('account.analytic.journal', 'crossovered_journal_rel', 'crossover_id', 'journal_id', 'Analytic Journal'),
        'ref': fields.many2one('account.analytic.account', 'Analytic Account Reference', required=True),
        'empty_line': fields.boolean('Dont show empty lines'),
    }
    _defaults = {
         'date1': lambda *a: time.strftime('%Y-01-01'),
         'date2': lambda *a: time.strftime('%Y-%m-%d'),
    }

    def print_report(self, cr, uid, ids, context=None):
        cr.execute('SELECT account_id FROM account_analytic_line')
        res = cr.fetchall()
        acc_ids = [x[0] for x in res]

        data = self.read(cr, uid, ids, context=context)[0]
        data['ref'] = data['ref'][0]

        obj_acc = self.pool.get('account.analytic.account').browse(cr, uid, data['ref'], context=context)
        name = obj_acc.name

        account_ids = self.pool.get('account.analytic.account').search(cr, uid, [('parent_id', 'child_of', [data['ref']])], context=context)

        flag = True
        for acc in account_ids:
            if acc in acc_ids:
                flag = False
                break
        if flag:
            raise UserError(_('There are no analytic lines related to account %s.' % name))

        datas = {
             'ids': [],
             'model': 'account.analytic.account',
             'form': data
        }
        return self.pool['report'].get_action(cr, uid, [], 'account_analytic_plans.report_crossoveredanalyticplans', data=datas, context=context)
