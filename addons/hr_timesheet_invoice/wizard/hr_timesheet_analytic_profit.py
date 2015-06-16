# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.exceptions import UserError


class account_analytic_profit(osv.osv_memory):
    _name = 'hr.timesheet.analytic.profit'
    _description = 'Print Timesheet Profit'
    _columns = {
        'date_from': fields.date('From', required=True),
        'date_to': fields.date('To', required=True),
        'journal_ids': fields.many2many('account.analytic.journal', 'analytic_profit_journal_rel', 'analytic_id', 'journal_id', 'Journal', required=True),
        'employee_ids': fields.many2many('res.users', 'analytic_profit_emp_rel', 'analytic_id', 'emp_id', 'User', required=True),
    }

    def _date_from(*a):
        return datetime.date.today().replace(day=1).strftime('%Y-%m-%d')

    def _date_to(*a):
        return datetime.date.today().strftime('%Y-%m-%d')

    _defaults = {
        'date_from': _date_from,
        'date_to': _date_to
    }

    def print_report(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('account.analytic.line')
        data = {}
        data['form'] = self.read(cr, uid , ids, context=context)[0]
        ids_chk = line_obj.search(cr, uid, [
                ('date', '>=', data['form']['date_from']),
                ('date', '<=', data['form']['date_to']),
                ('journal_id', 'in', data['form']['journal_ids']),
                ('user_id', 'in', data['form']['employee_ids']),
                ], context=context)
        if not ids_chk:
            raise UserError(_('No record(s) found for this report.'))

        data['form']['journal_ids'] = [(6, 0, data['form']['journal_ids'])] # Improve me => Change the rml/sxw so that it can support withou [0][2]
        data['form']['employee_ids'] = [(6, 0, data['form']['employee_ids'])]
        datas = {
            'ids': [],
            'model': 'account.analytic.line',
            'form': data['form']
        }
        return self.pool['report'].get_action(
            cr, uid, [], 'hr_timesheet_invoice.report_analyticprofit', data=datas, context=context
        )
