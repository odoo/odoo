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
import datetime
from mx.DateTime import *

from osv import osv, fields
from tools.translate import _

class account_aged_trial_balance(osv.osv_memory):

    _name = 'account.aged.trial.balance'
    _description = 'Account Aged Trial balance Report'

    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'period_length':fields.integer('Period length (days)', required=True),
        'date1': fields.date('Start of period', required=True),
        'result_selection': fields.selection([('customer','Receivable'),
                                              ('supplier','Payable'),
                                              ('all','Receivable and Payable')],
                                              'Filter on Partners', required=True),
        'direction_selection': fields.selection([('past','Past'),
                                                 ('future','Future')],
                                                 'Analysis Direction', required=True),
        }

    def _get_company(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        if context is None:
            context = {}
        user = user_obj.browse(cr, uid, uid, context=context)
        if user.company_id:
           return user.company_id.id
        else:
           return company_obj.search(cr, uid, [('parent_id', '=', False)])[0]

    _defaults = {
        'company_id': _get_company,
        'period_length': 30,
        'date1' : time.strftime('%Y-%m-%d'),
        'result_selection': 'all',
        'direction_selection': 'past',
                 }

    def calc_dates(self, cr, uid, ids, context=None):
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        data={}
        res = {}
        if context is None:
            context = {}
        data['ids'] = context.get('active_ids',[])
        data['model'] = 'res.partner'
        data['form'] = self.read(cr, uid, ids, [])[0]
        data['form']['fiscalyear'] = fiscalyear_obj.find(cr, uid)
        period_length = data['form']['period_length']
        if period_length<=0:
            raise osv.except_osv(_('UserError'), _('You must enter a period length that cannot be 0 or below !'))
        start = datetime.date.fromtimestamp(time.mktime(time.strptime(data['form']['date1'],"%Y-%m-%d")))
        start = DateTime(int(start.year),int(start.month),int(start.day))
        if data['form']['direction_selection'] == 'past':
            for i in range(5)[::-1]:
                stop = start - RelativeDateTime(days=period_length)
                res[str(i)] = {
                    'name' : str((5-(i+1))*period_length) + '-' + str((5-i)*period_length),
                    'stop': start.strftime('%Y-%m-%d'),
                    'start' : stop.strftime('%Y-%m-%d'),
                    }
                start = stop - RelativeDateTime(days=1)
        else:
            for i in range(5):
                stop = start + RelativeDateTime(days=period_length)
                res[str(5-(i+1))] = {
                    'name' : str((i)*period_length)+'-'+str((i+1)*period_length),
                    'start': start.strftime('%Y-%m-%d'),
                    'stop' : stop.strftime('%Y-%m-%d'),
                    }
                start = stop + RelativeDateTime(days=1)
        data['form'].update(res)
        return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.aged_trial_balance',
                'datas': data,
            }

account_aged_trial_balance()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
