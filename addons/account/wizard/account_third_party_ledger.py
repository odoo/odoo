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

class account_partner_ledger(osv.osv_memory):
    """
    This wizard will provide the partner Ledger report by periods, between any two dates.
    """
    _name = 'account.partner.ledger'
    _description = 'Account Partner Ledger'
    _columns = {
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'state': fields.selection([('bydate','By Date'),
                                 ('byperiod','By Period'),
                                 ('all','By Date and Period'),
                                 ('none','No Filter')
                                 ],'Date/Period Filter'),
        'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscal year', help='Keep empty for all open fiscal year'),
        'periods': fields.many2many('account.period', 'period_ledger_rel', 'report_id', 'period_id', 'Periods', help='All periods if empty', states={'none':[('readonly',True)],'bydate':[('readonly',True)]}),
        'result_selection': fields.selection([('customer','Receivable Accounts'),
                                              ('supplier','Payable Accounts'),
                                              ('all','Receivable and Payable Accounts')],
                                              'Partner', required=True),
        'soldeinit': fields.boolean('Include initial balances'),
        'reconcil': fields.boolean('Include Reconciled Entries'),
        'page_split': fields.boolean('One Partner Per Page'),
        'date1': fields.date('Start date', required=True),
        'date2': fields.date('End date', required=True),
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

    _defaults={
               'state' :  'none',
               'date1' : time.strftime('%Y-01-01'),
               'date2' : time.strftime('%Y-%m-%d'),
               'result_selection' : 'all',
               'reconcile' : True,
               'soldeinit' : True,
               'page_split' : False,
               'company_id' : _get_company,
               'fiscalyear' : False,
               }

    def check_state(self, cr, uid, ids, context=None):
        obj_fiscalyear = self.pool.get('account.fiscalyear')
        obj_periods = self.pool.get('account.period')
        if context is None:
            context = {}
        data={}
        data['ids'] = context.get('active_ids',[])
        data['form'] = self.read(cr, uid, ids, [])[0]
        data['form']['fiscalyear'] = obj_fiscalyear.find(cr, uid)
        data['form']['periods'] = obj_periods.search(cr, uid, [('fiscalyear_id','=',data['form']['fiscalyear'])])
        data['form']['display_account']='bal_all'
        data['model'] = 'ir.ui.menu'
        acc_id = self.pool.get('account.invoice').search(cr, uid, [('state','=','open')])
        if not acc_id:
                raise osv.except_osv(_('No Data Available'), _('No records found for your selection!'))
        if data['form']['state'] == 'bydate' or data['form']['state'] == 'all':
           data['form']['fiscalyear'] = False
        else :
           data['form']['fiscalyear'] = True
           return self._check_date(cr, uid, data, context)
        if data['form']['page_split']:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.third_party_ledger',
                'datas': data,
                'nodestroy':True,
            }
        else:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'account.third_party_ledger_other',
                'datas': data,
                'nodestroy':True,
            }

    def _check_date(self, cr, uid, data, context=None):
        if context is None:
            context = {}
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
                    'report_name': 'account.third_party_ledger',
                    'datas': data,
                    'nodestroy':True,
                }
        else:
            raise osv.except_osv(_('UserError'),_('Date not in a defined fiscal year'))

account_partner_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
