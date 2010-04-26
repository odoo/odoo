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

from tools.translate import _
from osv import fields, osv

class account_partner_balance(osv.osv_memory):
    """
    This wizard will provide the partner balance report by periods, between any two dates.
    """
    _name = 'account.partner.balance'
    _description = 'Account Partner Balance'
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'state': fields.selection([('bydate','By Date'),
                                 ('byperiod','By Period'),
                                 ('all','By Date and Period'),
                                 ('none','No Filter')
                                 ],'Date/Period Filter'),
        'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscal year', help='Keep empty for all open fiscal year'),
        'periods': fields.many2many('account.period', 'period_report_rel', 'report_id', 'period_id', 'Periods', help='All periods if empty'),
        'result_selection': fields.selection([('customer','Receivable Accounts'),
                                              ('supplier','Payable Accounts'),
                                              ('all','Receivable and Payable Accounts')],
                                              'Partner', required=True),
        'soldeinit': fields.boolean('Include initial balances'),
        'date1': fields.date('Start date', required=True),
        'date2': fields.date('End date', required=True),
            }

    def _get_company(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users')
        company_obj = self.pool.get('res.company')
        user = user_obj.browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        else:
            return company_obj.search(cr, uid, [('parent_id', '=', False)])[0]

    _defaults={
               'state' :  'none',
               'date1' : time.strftime('%Y-01-01'),
               'date2' : time.strftime('%Y-%m-%d'),
               'result_selection' : 'all',
               'soldeinit' : True,
               'company_id' : _get_company,
               'fiscalyear' : False,
               }

    def check_state(self, cr, uid, ids, context=None):
        data = {
            'ids':[],
            'model': 'res.partner',
            'form': self.read(cr, uid, ids, [])[0],
            }

        if data['form']['state'] == 'bydate'  :
           return self._check_date(cr, uid, data, context)
        if data['form']['state'] == 'byperiod':
            if not data['form']['periods']:
                raise  osv.except_osv(_('Warning'),_('Please Enter Periods ! '))

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.partner.balance',
            'datas': data,
            }

    def _check_date(self, cr, uid, data, context):
        sql = """
            SELECT f.id, f.date_start, f.date_stop FROM account_fiscalyear f  Where %s between f.date_start and f.date_stop """
        cr.execute(sql,(data['form']['date1'],))
        res = cr.dictfetchall()
        if res:
            if (data['form']['date2'] > res[0]['date_stop'] or data['form']['date2'] < res[0]['date_start']):
                raise  osv.except_osv(_('UserError'),_('Date to must be set between %s and %s') % (str(res[0]['date_start']), str(res[0]['date_stop'])))
            else:
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.partner.balance',
                    'datas': data,
                    }
        else:
            raise osv.except_osv(_('UserError'),_('Date not in a defined fiscal year'))

account_partner_balance()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

