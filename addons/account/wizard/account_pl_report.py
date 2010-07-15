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

from osv import osv, fields
from tools.translate import _

class account_pl_report(osv.osv_memory):
    """
    This wizard will provide the account profit and loss report by periods, between any two dates.
    """
    _name = 'account.pl.report'
    _description = 'Account Profit And Loss Report'
    _columns = {
        'Account_list': fields.many2one('account.account', 'Chart account',
                                required=True, domain = [('parent_id','=',False)]),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'display_account': fields.selection([('bal_movement','With movements'),
                                             ('bal_solde','With balance is not equal to 0'),
                                             ('bal_all','All'),
                                             ],'Display accounts'),
        'display_type': fields.boolean("Landscape Mode"),
        'fiscalyear': fields.many2one('account.fiscalyear', 'Fiscal year', help='Keep empty for all open fiscal year'),
        'state': fields.selection([('bydate','By Date'),
                                 ('byperiod','By Period'),
                                 ('all','By Date and Period'),
                                 ('none','No Filter')
                                 ],'Date/Period Filter'),
        'periods': fields.many2many('account.period', 'period_account_balance_rel',
                                    'report_id', 'period_id', 'Periods',
                                    help='Keep empty for all open fiscal year'),
        'date_from': fields.date('Start date', required=True),
        'date_to': fields.date('End date', required=True),
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
        'state' : 'none',
        'date_from' : time.strftime('%Y-01-01'),
        'date_to' : time.strftime('%Y-%m-%d'),
        'company_id' : _get_company,
        'fiscalyear' : False,
        'display_account': 'bal_all',
        'display_type': True,
        }

    def next_view(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [])[0]
        context.update({'Account_list': data['Account_list']})
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','account_pl_report_view')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])[0]['res_id']
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.pl.report',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }

    def check_state(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        data={}
        data['ids'] = context['active_ids']
        data['form'] = self.read(cr, uid, ids, ['date_from',  'company_id',  'state', 'periods', 'date_to',  'display_account',  'display_type', 'fiscalyear'])[0]
        data['form']['Account_list'] = context.get('Account_list',[])
        data['form']['context'] = context
        if data['form']['Account_list']:
            data['model'] = 'ir.ui.menu'
        else:
            data['model'] = 'account.account'

        if data['form']['state'] == 'bydate'  :
           return self._check_date(cr, uid, data, context)
        elif data['form']['state'] == 'byperiod':
            if not data['form']['periods']:
                raise  osv.except_osv(_('Warning'),_('Please Enter Periods ! '))
        if data['form']['display_type']:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pl.account.horizontal',
                'datas': data,
                'nodestroy':True,
                }
        else:
            return {
                'type': 'ir.actions.report.xml',
                'report_name': 'pl.account',
                'datas': data,
                'nodestroy':True,
                }
            
    def _check_date(self, cr, uid, data, context=None):
        if context is None:
            context = {}
        sql = """
            SELECT f.id, f.date_start, f.date_stop FROM account_fiscalyear f  Where %s between f.date_start and f.date_stop """
        cr.execute(sql,(data['form']['date_from'],))
        res = cr.dictfetchall()
        if res:

            if (data['form']['date_to'] > res[0]['date_stop'] or data['form']['date_to'] < res[0]['date_start']):
                raise  osv.except_osv(_('UserError'),_('Date to must be set between %s and %s') % (res[0]['date_start'], res[0]['date_stop']))
            else:
                if data['form']['display_type']:
                    return {
                        'type': 'ir.actions.report.xml',
                        'report_name': 'pl.account.horizontal',
                        'datas': data,
                        'nodestroy':True,
                        }
                else:
                    return {
                        'type': 'ir.actions.report.xml',
                        'report_name': 'pl.account',
                        'datas': data,
                        'nodestroy':True,
                        }
        else:
            raise osv.except_osv(_('UserError'),_('Date not in a defined fiscal year'))

account_pl_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
