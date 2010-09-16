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
import re

import rml_parse
from report import report_sxw
from common_report_header import common_report_header

class third_party_ledger(rml_parse.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        super(third_party_ledger, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'sum_debit_partner': self._sum_debit_partner,
            'sum_credit_partner': self._sum_credit_partner,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'get_currency': self._get_currency,
            'comma_me' : self.comma_me,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_account': self._get_account,
            'get_filter': self._get_filter,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_fiscalyear': self._get_fiscalyear,
            'get_start_date':self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_journal': self._get_journal,
            'get_partners':self._get_partners,
            'get_intial_balance':self._get_intial_balance,
            'display_initial_balance':self._display_initial_balance,
            'display_currency':self._display_currency,
        })

    def set_context(self, objects, data, ids, report_type=None):
        self.query = data['form'].get('query_line', '')
        self.init_query = data['form'].get('initial_bal_query', '')
        self.reconcil = data['form'].get('reconcil', True)
        self.initial_balance = data['form'].get('initial_balance', True)
        self.result_selection = data['form'].get('result_selection', 'customer')
        self.amount_currency = data['form'].get('amount_currency', False)
        PARTNER_REQUEST = ''
        if (data['model'] == 'res.partner'):
            ## Si on imprime depuis les partenaires
            if ids:
                PARTNER_REQUEST =  "AND line.partner_id IN %s",(tuple(ids),)
        if self.result_selection == 'supplier':
            self.ACCOUNT_TYPE = ['payable']
        elif self.result_selection == 'customer':
            self.ACCOUNT_TYPE = ['receivable']
        else:
            self.ACCOUNT_TYPE = ['payable','receivable']

        self.cr.execute(
            "SELECT a.id " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.type=t.code) " \
                'WHERE a.type IN %s' \
                "AND a.active", (tuple(self.ACCOUNT_TYPE), ))
        self.account_ids = [a for (a,) in self.cr.fetchall()]
        partner_to_use = []
        self.cr.execute(
                "SELECT DISTINCT l.partner_id " \
                "FROM account_move_line AS l, account_account AS account " \
                "WHERE l.partner_id IS NOT NULL " \
                    "AND l.account_id = account.id " \
                    "AND " + self.query +" " \
                    "AND l.account_id IN %s " \
                    " " + PARTNER_REQUEST + " " \
                    "AND account.active " ,
                (tuple(self.account_ids),))

        res = self.cr.dictfetchall()
        for res_line in res:
            partner_to_use.append(res_line['partner_id'])
        new_ids = partner_to_use
        self.partner_ids = new_ids
        objects = self.pool.get('res.partner').browse(self.cr, self.uid, new_ids)
        return super(third_party_ledger, self).set_context(objects, data, new_ids, report_type)

    def comma_me(self, amount):
        if type(amount) is float :
            amount = str('%.2f'%amount)
        else :
            amount = str(amount)
        if (amount == '0'):
             return ' '
        orig = amount
        new = re.sub("^(-?\d+)(\d{3})", "\g<1>'\g<2>", amount)
        if orig == new:
            return new
        else:
            return self.comma_me(new)

    def lines(self, partner):
        full_account = []
        if self.reconcil:
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND l.reconcile_id IS NULL"
        self.cr.execute(
            "SELECT l.id,l.date,j.code, l.ref, m.name as move_name, l.name, l.debit, l.credit,l.amount_currency,c.code AS currency_code " \
            "FROM account_move_line l " \
            "LEFT JOIN account_journal j " \
                "ON (l.journal_id = j.id) " \
            "LEFT JOIN res_currency c on (l.currency_id=c.id)" \
            "LEFT JOIN account_move m on (m.id=l.move_id)" \
            "WHERE l.partner_id = %s " \
                "AND l.account_id IN %s AND " + self.query +" " \
                " " + RECONCILE_TAG + " "\
                "ORDER BY l.date",
                (partner.id, tuple(self.account_ids)))
        res = self.cr.dictfetchall()
        sum = 0.0
        for r in res:
            sum = r['debit'] - r['credit']
            r['progress'] = sum
            full_account.append(r)
        return full_account

    def _get_intial_balance(self, partner):
        self.cr.execute(
            "SELECT COALESCE(SUM(l.debit),0.0), COALESCE(SUM(l.credit),0.0), COALESCE(sum(debit-credit), 0.0) " \
            "FROM account_move_line AS l " \
            "WHERE partner_id = %s " \
            "AND account_id IN %s" \
            "AND reconcile_id IS NULL  " \
            "AND " + self.init_query + "  ",
            (partner.id, tuple(self.account_ids)))
        return self.cr.fetchall()

    def _sum_debit_partner(self, partner):
        result_tmp = 0.0
        if self.reconcil :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        self.cr.execute(
                "SELECT sum(debit) " \
                "FROM account_move_line AS l " \
                "WHERE partner_id = %s " \
                    "AND account_id IN %s" \
                    " " + RECONCILE_TAG + " " \
                    "AND " + self.query + " " ,
                (partner.id,tuple(self.account_ids),))

        contemp = self.cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0
        return result_tmp

    def _sum_credit_partner(self, partner):
        result_tmp = 0.0
        if self.reconcil :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        self.cr.execute(
                "SELECT sum(credit) " \
                "FROM account_move_line AS l " \
                "WHERE partner_id=%s " \
                    "AND account_id IN %s" \
                    " " + RECONCILE_TAG + " " \
                    "AND " + self.query + " " ,
                (partner.id, tuple(self.account_ids),))

        contemp = self.cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0
        return result_tmp

    def _sum_debit(self):
        if not self.ids:
            return 0.0
        result_tmp = 0.0
        result_init = 0.0
        if self.reconcil :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        if self.initial_balance:
            self.cr.execute(
                    "SELECT sum(debit) " \
                    "FROM account_move_line AS l " \
                    "WHERE partner_id IN %s" \
                        "AND account_id IN %s" \
                        "AND reconcile_id IS NULL " \
                        "AND " + self.init_query + " ",
                    (tuple(self.partner_ids), tuple(self.account_ids)))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_tmp + 0.0

        self.cr.execute(
                "SELECT sum(debit) " \
                "FROM account_move_line AS l " \
                "WHERE partner_id IN %s" \
                    "AND account_id IN %s" \
                    " " + RECONCILE_TAG + " " \
                    "AND " + self.query + " " ,
                    (tuple(self.partner_ids), tuple(self.account_ids),))
        contemp = self.cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0
        return result_tmp  + result_init

    def _sum_credit(self):
        if not self.ids:
            return 0.0
        result_tmp = 0.0
        result_init = 0.0
        if self.reconcil :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        if self.initial_balance:
            self.cr.execute(
                    "SELECT sum(credit) " \
                    "FROM account_move_line AS l " \
                    "WHERE partner_id IN %s" \
                        "AND account_id IN %s" \
                        "AND reconcile_id IS NULL " \
                        "AND " + self.init_query + " ",
                    (tuple(self.partner_ids), tuple(self.account_ids)))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_init = contemp[0] or 0.0
            else:
                result_init = result_tmp + 0.0

        self.cr.execute(
                "SELECT sum(credit) " \
                "FROM account_move_line AS l " \
                "WHERE partner_id  IN %s" \
                    "AND account_id IN %s" \
                    " " + RECONCILE_TAG + " " \
                    "AND " + self.query + " " ,
                    (tuple(self.partner_ids), tuple(self.account_ids),))
        contemp = self.cr.fetchone()
        if contemp != None:
            result_tmp = contemp[0] or 0.0
        else:
            result_tmp = result_tmp + 0.0

        return result_tmp  + result_init
#
    def _get_partners(self):
        if self.result_selection == 'customer':
            return 'Receivable Accounts'
        elif self.result_selection == 'supplier':
            return 'Payable Accounts'
        elif self.result_selection == 'customer_supplier':
            return 'Receivable and Payable Accounts'
        return ''

    def _sum_currency_amount_account(self, account, form):
        self._set_get_account_currency_code(account.id)
        self.cr.execute("SELECT sum(aml.amount_currency) FROM account_move_line as aml,res_currency as rc WHERE aml.currency_id = rc.id AND aml.account_id= %s ", (account.id,))
        total = self.cr.fetchone()
        if self.account_currency:
            return_field = str(total[0]) + self.account_currency
            return return_field
        else:
            currency_total = self.tot_currency = 0.0
            return currency_total

    def _display_initial_balance(self, data):
         if self.initial_balance:
             return True
         return False

    def _display_currency(self, data):
         if self.amount_currency :
             return True
         return False

report_sxw.report_sxw('report.account.third_party_ledger', 'res.partner',
        'addons/account/report/account_partner_ledger.rml',parser=third_party_ledger,
        header='internal')

report_sxw.report_sxw('report.account.third_party_ledger_other', 'res.partner',
        'addons/account/report/account_partner_ledger_other.rml',parser=third_party_ledger,
        header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
