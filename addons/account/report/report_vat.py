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

from openerp import models,api
from common_report_header import common_report_header


class AccountTaxReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_vat'

    @api.multi
    def _get_basedon(self, data):
        return data.get('form', False) and data['form'].get('based_on', False)

    @api.multi
    def _get_lines(self, based_on, company_id=False, parent=False, level=0):
        res = self._get_codes(based_on, company_id, parent, level)

        i = 0
        top_result = []
        while i < len(res):

            res_dict = { 'code': res[i][1].code,
                'name': res[i][1].name,
                'debit': 0,
                'credit': 0,
                'tax_amount': res[i][1].sum,
                'type': 1,
                'level': res[i][0],
                'pos': 0
            }

            top_result.append(res_dict)
            res_general = self._get_general(res[i][1].id, company_id, based_on)
            ind_general = 0
            while ind_general < len(res_general):
                res_general[ind_general]['type'] = 2
                res_general[ind_general]['pos'] = 0
                res_general[ind_general]['level'] = res_dict['level']
                top_result.append(res_general[ind_general])
                ind_general+=1
            i+=1
        return top_result

    @api.multi
    def _get_general(self, tax_code_id, company_id, based_on):
        if not self.data['form'].get('display_detail'):
            return []
        res = []
        obj_account = self.env['account.account']
        if based_on == 'payments':
            self._cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND move.id = line.move_id \
                        AND line.date IN %s \
                        AND ((invoice.state = %s) \
                            OR (invoice.id IS NULL))  \
                    GROUP BY account.id,account.name,account.code', (tax_code_id,
                        company_id, 'paid'))

        else:
            self._cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account \
                    WHERE line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND line.date = %s\
                        AND NOT account.deprecated \
                    GROUP BY account.id,account.name,account.code', (tax_code_id,
                        company_id))
        res = self._cr.dictfetchall()

        i = 0
        while i<len(res):
            res[i]['account'] = obj_account.browse(res[i]['account_id'])
            i+=1
        return res

    @api.multi
    def _get_codes(self, based_on, company_id, parent=False, level=0):
        obj_tc = self.env['account.tax.code']
        codes = obj_tc.search([('parent_id','=',parent),('company_id','=',company_id)], order='sequence')
        res = []
        for code in codes:
            res.append(('.'*2*level, code))
            res += self._get_codes(based_on, company_id, code.id, level+1)
        return res

    @api.multi
    def _add_codes(self, based_on, account_list=None):
        if account_list is None:
            account_list = []
        res = []
        obj_tc = self.env['account.tax.code']
        for account in account_list:
            sum_tax_add = 0
            for code in obj_tc.browse([account[1].id]):
                sum_tax_add = sum_tax_add + code.sum
                code.sum = sum_tax_add
                res.append((account[0], code))
        return res

    @api.multi
    def render_html(self, data=None):
        self.data = data
        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_vat')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': [],
            'get_account': self._get_account(data),
            'get_fiscalyear': self._get_fiscalyear(data),
            'get_start_date': self._get_start_date(data),
            'get_end_date': self._get_end_date(data),
            'get_basedon': self._get_basedon(data),
            'get_lines': self._get_lines(data['form']['based_on'], data['form']['company_id'])
        }
        return report_obj.render('account.report_vat', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
