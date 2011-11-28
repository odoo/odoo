##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import pooler
from report import report_sxw
from common_report_header import common_report_header
from tools.translate import _

class report_pl_account_horizontal(report_sxw.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        super(report_pl_account_horizontal, self).__init__(cr, uid, name, context=context)
        self.result_sum_dr = 0.0
        self.result_sum_cr = 0.0
        self.res_pl = {}
        self.result = {}
        self.result_temp = []
        self.localcontext.update( {
            'time': time,
            'get_lines': self.get_lines,
            'get_lines_another': self.get_lines_another,
            'get_currency': self._get_currency,
            'get_data': self.get_data,
            'sum_dr': self.sum_dr,
            'sum_cr': self.sum_cr,
            'final_result': self.final_result,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_sortby': self._get_sortby,
            'get_filter': self._get_filter,
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_company':self._get_company,
            'get_target_move': self._get_target_move,
        })
        self.context = context

    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        if (data['model'] == 'ir.ui.menu'):
            new_ids = 'chart_account_id' in data['form'] and [data['form']['chart_account_id']] or []
            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)
        return super(report_pl_account_horizontal, self).set_context(objects, data, new_ids, report_type=report_type)


    def final_result(self):
        return self.res_pl

    def sum_dr(self):
        if self.res_pl['type'] == _('Net Profit'):
            self.result_sum_dr += self.res_pl['balance']
        return self.result_sum_dr

    def sum_cr(self):
        if self.res_pl['type'] == _('Net Loss'):
            self.result_sum_cr += self.res_pl['balance']
        return self.result_sum_cr

    def get_data(self, data):
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(self.cr.dbname)

        account_pool = db_pool.get('account.account')
        currency_pool = db_pool.get('res.currency')

        types = [
            'expense',
            'income'
                ]

        ctx = self.context.copy()
        ctx['fiscalyear'] = data['form'].get('fiscalyear_id', False)

        if data['form']['filter'] == 'filter_period':
            ctx['period_from'] = data['form'].get('period_from', False)
            ctx['period_to'] =  data['form'].get('period_to', False)
        elif data['form']['filter'] == 'filter_date':
            ctx['date_from'] = data['form'].get('date_from', False)
            ctx['date_to'] =  data['form'].get('date_to', False)

        cal_list = {}
        account_id = data['form'].get('chart_account_id', False)
        company_currency = account_pool.browse(self.cr, self.uid, account_id).company_id.currency_id
        account_ids = account_pool._get_children_and_consol(cr, uid, account_id, context=ctx)
        accounts = account_pool.browse(cr, uid, account_ids, context=ctx)

        for typ in types:
            accounts_temp = []
            for account in accounts:
                if (account.user_type.report_type) and (account.user_type.report_type == typ):
                    currency = account.currency_id and account.currency_id or account.company_id.currency_id
                    if typ == 'expense' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_dr += account.debit - account.credit
                    if typ == 'income' and account.type <> 'view' and (account.debit <> account.credit):
                        self.result_sum_cr += account.credit - account.debit
                    if data['form']['display_account'] == 'movement':
                        if not currency_pool.is_zero(self.cr, self.uid, currency, account.credit) or not currency_pool.is_zero(self.cr, self.uid, currency, account.debit) or not currency_pool.is_zero(self.cr, self.uid, currency, account.balance):
                            accounts_temp.append(account)
                    elif data['form']['display_account'] == 'not_zero':
                        if not currency_pool.is_zero(self.cr, self.uid, currency, account.balance):
                            accounts_temp.append(account)
                    else:
                        accounts_temp.append(account)
            if currency_pool.is_zero(self.cr, self.uid, company_currency, (self.result_sum_dr-self.result_sum_cr)):
                self.res_pl['type'] = None
                self.res_pl['balance'] = 0.0
            elif self.result_sum_dr > self.result_sum_cr:
                self.res_pl['type'] = _('Net Loss')
                self.res_pl['balance'] = (self.result_sum_dr - self.result_sum_cr)
            else:
                self.res_pl['type'] = _('Net Profit')
                self.res_pl['balance'] = (self.result_sum_cr - self.result_sum_dr)
            self.result[typ] = accounts_temp
            cal_list[typ] = self.result[typ]
        if cal_list:
            temp = {}
            for i in range(0,max(len(cal_list['expense']),len(cal_list['income']))):
                if i < len(cal_list['expense']) and i < len(cal_list['income']):
                    temp={
                          'code': cal_list['expense'][i].code,
                          'name': cal_list['expense'][i].name,
                          'level': cal_list['expense'][i].level,
                          'balance': cal_list['expense'][i].balance != 0 and \
                                    cal_list['expense'][i].balance * cal_list['expense'][i].user_type.sign or \
                                    cal_list['expense'][i].balance,
                          'code1': cal_list['income'][i].code,
                          'name1': cal_list['income'][i].name,
                          'level1': cal_list['income'][i].level,
                          'balance1': cal_list['income'][i].balance != 0 and \
                                        cal_list['income'][i].balance * cal_list['income'][i].user_type.sign or \
                                        cal_list['income'][i].balance,
                          }
                    self.result_temp.append(temp)
                else:
                    if i < len(cal_list['income']):
                        temp={
                              'code': '',
                              'name': '',
                              'level': False,
                              'balance':False,
                              'code1': cal_list['income'][i].code,
                              'name1': cal_list['income'][i].name,
                              'level1': cal_list['income'][i].level,
                              'balance1': cal_list['income'][i].balance != 0 and \
                                            cal_list['income'][i].balance * cal_list['income'][i].user_type.sign \
                                            or cal_list['income'][i].balance,
                              }
                        self.result_temp.append(temp)
                    if  i < len(cal_list['expense']):
                        temp={
                              'code': cal_list['expense'][i].code,
                              'name': cal_list['expense'][i].name,
                              'level': cal_list['expense'][i].level,
                              'balance': cal_list['expense'][i].balance != 0 and \
                                            cal_list['expense'][i].balance * cal_list['expense'][i].user_type.sign \
                                            or cal_list['expense'][i].balance,
                              'code1': '',
                              'name1': '',
                              'level1': False,
                              'balance1':False,
                              }
                        self.result_temp.append(temp)
        return None

    def get_lines(self):
        return self.result_temp

    def get_lines_another(self, group):
        return self.result.get(group, [])

report_sxw.report_sxw('report.pl.account.horizontal', 'account.account',
    'addons/account/report/account_profit_horizontal.rml',parser=report_pl_account_horizontal, header='internal landscape')

report_sxw.report_sxw('report.pl.account', 'account.account',
    'addons/account/report/account_profit_loss.rml',parser=report_pl_account_horizontal, header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
