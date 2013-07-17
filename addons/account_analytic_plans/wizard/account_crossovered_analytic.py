# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time

from openerp.osv import fields, osv
from openerp.tools.translate import _

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

        data = self.read(cr, uid, ids, [], context=context)[0]
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
            raise osv.except_osv(_('User Error!'),_('There are no analytic lines related to account %s.' % name))

        datas = {
             'ids': [],
             'model': 'account.analytic.account',
             'form': data
        }
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.analytic.account.crossovered.analytic',
            'datas': datas,
        }

account_crossovered_analytic()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
