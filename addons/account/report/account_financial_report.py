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

from openerp import models, api
from openerp.tools.translate import _
from common_report_header import common_report_header

class PartnerBbalanceReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_financial'

    @api.model
    def _get_lines(self, data):
        lines = []
        account_obj = self.env['account.account']
        financial_report_obj = self.env['account.financial.report']
        child_ids = financial_report_obj.with_context(data['form']['used_context']).browse([data['form']['account_report_id'][0]])._get_children_by_order()
        for report in financial_report_obj.browse(child_ids):
            vals = {
                'name': report.name,
                'balance': report.balance * report.sign or 0.0,
                'type': 'report',
                'level': bool(report.style_overwrite) and report.style_overwrite or report.level,
                'account_type': report.type =='sum' and 'view' or False, #used to underline the financial report balances
            }
            if data['form']['debit_credit']:
                vals['debit'] = report.debit
                vals['credit'] = report.credit
            if data['form']['enable_filter']:
                vals['balance_cmp'] = financial_report_obj.with_context(data['form']['comparison_context']).browse(report.id).balance * report.sign or 0.0
            lines.append(vals)
            account_ids = []
            if report.display_detail == 'no_detail':
                #the rest of the loop is used to display the details of the financial report, so it's not needed here.
                continue
            if report.type == 'accounts' and report.account_ids:
                account_ids = report.account_ids._get_children_and_consol()
            elif report.type == 'account_type' and report.account_type_ids:
                account_ids =  account_obj.search([('user_type','in', [x.id for x in report.account_type_ids])]).ids

            for account in account_obj.with_context(data['form']['used_context']).browse(account_ids):
                #if there are accounts to display, we add them to the lines with a level equals to their level in
                #the COA + 1 (to avoid having them with a too low level that would conflicts with the level of data
                #financial reports for Assets, liabilities...)
                flag = False
                vals = {
                    'name': account.code + ' ' + account.name,
                    'balance':  account.balance != 0 and account.balance * report.sign or account.balance,
                    'type': 'account',
                    'level': report.display_detail == 'detail_with_hierarchy' and min(account.level + 1,6) or 6, #account.level + 1
                    'account_type': account.internal_type,
                }
                if data['form']['debit_credit']:
                    vals['debit'] = account.debit
                    vals['credit'] = account.credit
                if not account.company_id.currency_id.is_zero(vals['balance']):
                    flag = True
                if data['form']['enable_filter']:
                    vals['balance_cmp'] = account_obj.with_context(data['form']['comparison_context']).browse(account.id).balance * report.sign or 0.0
                    if not account.company_id.currency_id.is_zero(vals['balance_cmp']):
                        flag = True
                if flag:
                    lines.append(vals)
        return lines

    @api.multi
    def render_html(self, data=None):
        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_financial')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': self,
            'data': data,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_target_move': self._get_target_move,
            'get_lines': self._get_lines
        }
        return report_obj.render('account.report_financial', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: