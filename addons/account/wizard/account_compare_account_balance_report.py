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

class account_compare_account_balance_report(osv.osv_memory):
    """
    This wizard will provide the account balance comparision report by fiscal years.
    """
    _name = 'account.compare.account.balance.report'
    _description = 'Account Balance Report'
    _columns = {
        'fiscalyear': fields.many2many('account.fiscalyear', 'account_fiscalyear_rel','account_id','fiscalyear_id','Fiscal year', help='Keep empty for all open fiscal year'),
        'select_account': fields.many2one('account.account','Select Reference Account(for  % comparision)',help='Keep empty for comparision to its parent'),
        'account_choice': fields.selection([('all','All accounts'),
                                            ('bal_zero','With balance is not equal to 0'),
                                            ('moves','With movements')],'Show Accounts'),
        'show_columns': fields.boolean('Show Debit/Credit Information'),
        'landscape': fields.boolean('Show Report in Landscape Form'),
        'format_perc': fields.boolean('Show Comparision in %'),
        'compare_pattern': fields.selection([('bal_cash','Cash'),
                                             ('bal_perc','Percentage'),
                                             ('none','Don'+ "'" +'t Compare')],'Compare Selected Years In Terms Of'),
        'period_manner': fields.selection([('actual','Financial Period'),('created','Creation Date')],'Entries Selection Based on'),
        'periods': fields.many2many('account.period', 'period_account_balance_rel',
                                    'report_id', 'period_id', 'Periods',
                                    help='Keep empty for all open fiscal year'),
        }

    _defaults={
        'compare_pattern': 'none',
        'account_choice': 'moves',
        'period_manner': 'actual',
        }

    def check(self, cr, uid, ids, context=None):
        data={}
        if context is None:
            context = {}
        data = {
            'ids':context['active_ids'],
            'form': self.read(cr, uid, ids, ['fiscalyear',  'select_account',  'account_choice', 'periods', 'show_columns',  'landscape',  'format_perc','compare_pattern','period_manner'])[0],
            }

        data['form']['context'] = context
        if (len(data['form']['fiscalyear'])==0) or (len(data['form']['fiscalyear'])>1 and (data['form']['compare_pattern']!='none') and (data['form']['format_perc']==1) and (data['form']['show_columns']==1) and (data['form']['landscape']!=1)):
            raise osv.except_osv(_('Warning !'), _('You have to select at least 1 Fiscal Year. \nYou may have selected the compare options with more than 1 year with credit/debit columns and % option.This can lead contents to be printed out of the paper.Please try again.'))


        if ((len(data['form']['fiscalyear'])==3) and (data['form']['format_perc']!=1) and (data['form']['show_columns']!=1)):
            if data['form']['landscape']==1:
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.account.balance.landscape',
                    'datas': data,
                    'nodestroy':True,
                    }
            else:
                return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.balance.account.balance',
                    'datas': data,
                    'nodestroy':True,
                    }
        if data['form']['format_perc']==1:
            if len(data['form']['fiscalyear'])<=2:
                if data['form']['landscape']==1:
                    return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.account.balance.landscape',
                    'datas': data,
                    'nodestroy':True,
                    }
                else:
                    return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.balance.account.balance',
                    'datas': data,
                    'nodestroy':True,
                    }
            else:
                if len(data['form']['fiscalyear'])==3:
                    if data['form']['landscape']==1:
                        return {
                            'type': 'ir.actions.report.xml',
                            'report_name': 'account.account.balance.landscape',
                            'datas': data,
                            'nodestroy':True,
                            }
                    else:
                        raise osv.except_osv(_('Warning !'), _('You might have done following mistakes. Please correct them and try again. \n 1. You have selected more than 3 years in any case. \n 2. You have not selected  Percentage option, but you have selected more than 2 years. \n You can select maximum 3 years. Please check again. \n 3. You have selected Percentage option with more than 2 years, but you have not selected landscape format. You have to select Landscape option. Please Check it.'))
                else:
                        raise osv.except_osv(_('Warning !'), _('You might have done following mistakes. Please correct them and try again. \n 1. You have selected more than 3 years in any case. \n 2. You have not selected  Percentage option, but you have selected more than 2 years. \n You can select maximum 3 years. Please check again. \n 3. You have selected Percentage option with more than 2 years, but you have not selected landscape format. You have to select Landscape option. Please Check it.'))
        else:
            if len(data['form']['fiscalyear'])>2:
                if data['form']['landscape']==1:
                    return {
                            'type': 'ir.actions.report.xml',
                            'report_name': 'account.account.balance.landscape',
                            'datas': data,
                            'nodestroy':True,
                            }
                else:
                        raise osv.except_osv(_('Warning !'), _('You might have done following mistakes. Please correct them and try again. \n 1. You have selected more than 3 years in any case. \n 2. You have not selected  Percentage option, but you have selected more than 2 years. \n You can select maximum 3 years. Please check again. \n 3. You have selected Percentage option with more than 2 years, but you have not selected landscape format. You have to select Landscape option. Please Check it.'))
            else:
                if data['form']['landscape']==1:
                    return {
                            'type': 'ir.actions.report.xml',
                            'report_name': 'account.account.balance.landscape',
                            'datas': data,
                            'nodestroy':True,
                            }
                else:
                    return {
                    'type': 'ir.actions.report.xml',
                    'report_name': 'account.balance.account.balance',
                    'datas': data,
                    'nodestroy':True,
                    }
account_compare_account_balance_report()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

