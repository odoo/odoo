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
from openerp import models, api
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from common_report_header import common_report_header

class AccountTaxReport(models.AbstractModel, common_report_header):
    _name = 'report.account.report_vat'

    @api.model
    def _get_lines(self, based_on, company_id=False, parent=False, level=0):
        date = self.date
        res = self._get_codes(based_on, company_id, parent, level, date)
        if date:
            res = self._add_codes(based_on, res, date)
        else:
            date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            res = self._add_codes(based_on, res, date)

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
            res_general = self._get_general(res[i][1].id, date, company_id, based_on)
            ind_general = 0
            while ind_general < len(res_general):
                res_general[ind_general]['type'] = 2
                res_general[ind_general]['pos'] = 0
                res_general[ind_general]['level'] = res_dict['level']
                top_result.append(res_general[ind_general])
                ind_general+=1
            i+=1
        return top_result

    @api.model
    def _get_general(self, tax_code_id, date, company_id, based_on):
        if not self.display_detail:
            return []
        res = []
        obj_account = self.env['account.account']
        date = date
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
                        company_id, date, 'paid'))

        else:
            self._cr.execute("SELECT SUM(line.tax_amount) AS tax_amount, \
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
                        AND account.deprecated = 'f' \
                    GROUP BY account.id,account.name,account.code", (tax_code_id,
                        company_id, date))
        res = self._cr.dictfetchall()

        i = 0
        while i<len(res):
            res[i]['account'] = obj_account.browse(res[i]['account_id'])
            i+=1
        return res

    @api.model
    def _get_codes(self, based_on, company_id, parent=False, level=0, date=None):
        codes = self.env['account.tax.code'].search([('parent_id','=',parent),('company_id','=',company_id)], order='sequence')
        res = []
        for code in codes:
            res.append(('.'*2*level, code))
            res += self._get_codes(based_on, company_id, code.id, level+1)
        return res

    @api.model
    def _add_codes(self, based_on, account_list=None, date=None):
        if account_list is None:
            account_list = []
        if date is None:
            date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
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
        self.date = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
        self.display_detail = data['form']['display_detail']
        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_vat')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': self,
            'data': data,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_lines': self._get_lines
        }
        return report_obj.render('account.report_vat', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
