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
import datetime

import pooler
import rml_parse
from report import report_sxw
from common_report_header import common_report_header

class third_party_ledger(rml_parse.rml_parse, common_report_header):

    def __init__(self, cr, uid, name, context=None):
        self.date_lst = []
        self.date_lst_string = ''
        super(third_party_ledger, self).__init__(cr, uid, name, context=context)
        self.localcontext.update( {
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
            'sum_currency_amount_account': self._sum_currency_amount_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_journal': self._get_journal,
            'get_partners':self._get_partners,

        })

    def date_range(self, start, end):
        if not start or not end:
            return []
        start = datetime.date.fromtimestamp(time.mktime(time.strptime(start,"%Y-%m-%d")))
        end = datetime.date.fromtimestamp(time.mktime(time.strptime(end,"%Y-%m-%d")))
        full_str_date = []
    #
        r = (end+datetime.timedelta(days=1)-start).days
    #
        date_array = [start+datetime.timedelta(days=i) for i in range(r)]
        for date in date_array:
            full_str_date.append(str(date))
        return full_str_date

    #
    def transform_period_into_date_array(self, data):
        ## Get All Period Date
        if not data['form']['periods']:
            periods_id =  self.pool.get('account.period').search(self.cr, self.uid, [('fiscalyear_id','=',data['form']['fiscalyear'])])
        else:
            periods_id = data['form']['periods']
        date_array = []
        for period_id in periods_id:
            period_obj = self.pool.get('account.period').browse(self.cr, self.uid, period_id)
            date_array = date_array + self.date_range(period_obj.date_start, period_obj.date_stop)
        self.date_lst = date_array
        self.date_lst.sort()

    def transform_date_into_date_array(self, data):
        return_array = self.date_range(data['form']['date_from'], data['form']['date_to'])
        self.date_lst = return_array
        self.date_lst.sort()

    def transform_none_into_date_array(self, data):
        sql = "SELECT min(date) as start_date from account_move_line"
        self.cr.execute(sql)
        start_date = self.cr.fetchone()[0]
        sql = "SELECT max(date) as start_date from account_move_line"
        self.cr.execute(sql)
        stop_date = self.cr.fetchone()[0]
        array= []
        array = array + self.date_range(start_date, stop_date)
        self.date_lst = array
        self.date_lst.sort()

    def comma_me(self, amount):
        if  type(amount) is float :
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

    def special_map(self):
        string_map = ''
        for date_string in self.date_lst:
            string_map = date_string + ','
        return string_map

    def set_context(self, objects, data, ids, report_type=None):
        PARTNER_REQUEST = ''
        if (data['model'] == 'res.partner'):
            ## Si on imprime depuis les partenaires
            if ids:
                #PARTNER_REQUEST =  "AND line.partner_id IN (" + ','.join(map(str, ids)) + ")"
                PARTNER_REQUEST =  "AND line.partner_id IN %s",(tuple(ids),)
        # Transformation des date
        #
        #
#        if data['form']['fiscalyear']:
#            self.transform_period_into_date_array(data)
#        else:
#            self.transform_date_into_date_array(data)
        ##
        if data['form']['filter'] == 'filter_no':
            self.transform_none_into_date_array(data)
        elif data['form']['filter'] == 'filter_date':
            self.transform_date_into_date_array(data)
        elif data['form']['filter'] == 'filter_period':
            self.transform_period_into_date_array(data)

        self.date_lst_string = ''
        if self.date_lst:
            self.date_lst_string = '\'' + '\',\''.join(map(str, self.date_lst)) + '\''
        #
        if data['form']['result_selection'] == 'supplier':
            self.ACCOUNT_TYPE = ['payable']
        elif data['form']['result_selection'] == 'customer':
            self.ACCOUNT_TYPE = ['receivable']
        else:
            self.ACCOUNT_TYPE = ['payable','receivable']

        self.cr.execute(
            "SELECT a.id " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.type=t.code) " \
#            "WHERE a.company_id = %s " \
                'WHERE a.type IN %s' \
                "AND a.active", (tuple(self.ACCOUNT_TYPE), ))
        self.account_ids = [a for (a,) in self.cr.fetchall()]
        partner_to_use = []

        if self.date_lst and data['form']['soldeinit'] :
            self.cr.execute(
                "SELECT DISTINCT line.partner_id " \
                "FROM account_move_line AS line, account_account AS account " \
                "WHERE line.partner_id IS NOT NULL " \
                    "AND line.account_id = account.id " \
                    "AND line.date >= %s " \
                    "AND line.date <= %s " \
                    "AND line.reconcile_id IS NULL " \
                    "AND line.account_id IN %s" \
                    " " + PARTNER_REQUEST + " " \
#                    "AND account.company_id = %s " \
                    "AND account.active " ,
                (self.date_lst[0],self.date_lst[len(self.date_lst)-1],tuple(self.account_ids),))
#        else:
#
#            self.cr.execute(
#                "SELECT DISTINCT line.partner_id " \
#                "FROM account_move_line AS line, account_account AS account " \
#                "WHERE line.partner_id IS NOT NULL " \
#                    "AND line.account_id = account.id " \
#                    "AND line.date IN (" + self.date_lst_string + ") " \
#                    "AND line.account_id IN (" + self.account_ids + ") " \
#                    " " + PARTNER_REQUEST + " " \
#                    "AND account.company_id = %s " \
#                    "AND account.active " ,
#                (data['form']['company_id']))

        res = self.cr.dictfetchall()

        for res_line in res:
                partner_to_use.append(res_line['partner_id'])
        new_ids = partner_to_use

        #self.partner_ids = ','.join(map(str, new_ids))
        self.partner_ids = new_ids
        objects = self.pool.get('res.partner').browse(self.cr, self.uid, new_ids)
        super(third_party_ledger, self).set_context(objects, data, new_ids, report_type)

    def lines(self, partner,data):
        full_account = []
        if data['form']['reconcil'] :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND l.reconcile_id IS NULL"

#        if data['form']['soldeinit'] :
#
#            self.cr.execute(
#                    "SELECT l.id,l.date,j.code, l.ref, l.name, l.debit, l.credit " \
#                    "FROM account_move_line l " \
#                    "LEFT JOIN account_journal j " \
#                        "ON (l.journal_id = j.id) " \
#                    "WHERE l.partner_id = %s " \
#                        "AND l.account_id IN (" + self.account_ids + ") " \
#                        "AND l.date <= %s " \
#                        "AND l.reconcile_id IS NULL "
#                    "ORDER BY l.id",
#                    (partner.id, self.date_lst[0]))
#            res = self.cr.dictfetchall()
#            print"----res----",res
#            sum = 0.0
#            for r in res:
#                sum = r['debit'] - r['credit']
#                r['progress'] = sum
#                full_account.append(r)
        if self.date_lst_string:
            self.cr.execute(
                "SELECT l.id,l.date,j.code, l.ref, l.name, l.debit, l.credit " \
                "FROM account_move_line l " \
                "LEFT JOIN account_journal j " \
                    "ON (l.journal_id = j.id) " \
                "WHERE l.partner_id = %s " \
                    "AND l.account_id IN %s"\
                    "AND l.date IN (" + self.date_lst_string + ")"
                    " " + RECONCILE_TAG + " "\
                    "ORDER BY l.id",
                    (partner.id, tuple(self.account_ids),))
            res = self.cr.dictfetchall()
            sum = 0.0
            for r in res:
                sum = r['debit'] - r['credit']
                r['progress'] = sum
                full_account.append(r)
        return full_account

    def _sum_debit_partner(self, partner, data):
        result_tmp = 0.0
        if data['form']['reconcil'] :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        if self.date_lst and data['form']['soldeinit'] :
            self.cr.execute(
                "SELECT sum(debit) " \
                "FROM account_move_line " \
                "WHERE partner_id = %s " \
                    "AND account_id IN %s" \
                    "AND reconcile_id IS NULL " \
                    "AND date < %s " ,
                (partner.id, tuple(self.account_ids), self.date_lst[0],))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0

        if self.date_lst_string:
            self.cr.execute(
                    "SELECT sum(debit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id = %s " \
                        "AND account_id IN %s" \
                        " " + RECONCILE_TAG + " " \
                        "AND date IN (" + self.date_lst_string + ")" ,
                    (partner.id,tuple(self.account_ids),))

            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0
        return result_tmp

    def _sum_credit_partner(self, partner, data):
        result_tmp = 0.0
        if data['form']['reconcil'] :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        if self.date_lst and data['form']['soldeinit'] :
            self.cr.execute(
                    "SELECT sum(credit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id=%s " \
                        "AND account_id IN %s" \
                        "AND reconcile_id IS NULL " \
                        "AND date < %s " ,
                    (partner.id, tuple(self.account_ids), self.date_lst[0],))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0

        if self.date_lst_string:
            self.cr.execute(
                    "SELECT sum(credit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id=%s " \
                        "AND account_id IN %s" \
                        " " + RECONCILE_TAG + " " \
                        "AND date IN (" + self.date_lst_string + ")",
                    (partner.id, tuple(self.account_ids),))

            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0
        return result_tmp

    def _sum_debit(self, data):
        if not self.ids:
            return 0.0
        result_tmp = 0.0
        if data['form']['reconcil'] :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        if self.date_lst and data['form']['soldeinit'] :
            self.cr.execute(
                    "SELECT sum(debit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id IN %s" \
                        "AND account_id IN %s" \
                        "AND reconcile_id IS NULL " \
                        "AND date < %s " ,
                    (tuple(self.partner_ids), tuple(self.account_ids), self.date_lst[0],))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0

        if self.date_lst_string:
            self.cr.execute(
                    "SELECT sum(debit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id IN %s" \
                        "AND account_id IN %s" \
                        " " + RECONCILE_TAG + " " \
                        "AND date IN (" + self.date_lst_string + ")",(tuple(self.partner_ids), tuple(self.account_ids),))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0
        return result_tmp

    def _sum_credit(self, data):
        if not self.ids:
            return 0.0
        result_tmp = 0.0
        if data['form']['reconcil'] :
            RECONCILE_TAG = " "
        else:
            RECONCILE_TAG = "AND reconcile_id IS NULL"
        if self.date_lst and data['form']['soldeinit'] :
            self.cr.execute(
                    "SELECT sum(credit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id IN %s" \
                        "AND account_id IN %s" \
                        "AND reconcile_id IS NULL " \
                        "AND date < %s " ,
                    (tuple(self.partner_ids), tuple(self.account_ids), self.date_lst[0],))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0

        if self.date_lst_string:
            self.cr.execute(
                    "SELECT sum(credit) " \
                    "FROM account_move_line " \
                    "WHERE partner_id  IN %s" \
                        "AND account_id IN %s" \
                        " " + RECONCILE_TAG + " " \
                        "AND date IN (" + self.date_lst_string + ")",(tuple(self.partner_ids), tuple(self.account_ids),))
            contemp = self.cr.fetchone()
            if contemp != None:
                result_tmp = contemp[0] or 0.0
            else:
                result_tmp = result_tmp + 0.0
        return result_tmp
#
#    def _get_company(self, form):
#        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

    def _get_currency(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name

    def _get_partners(self, data):
        if data['form']['result_selection']=='customer':
            return 'Receivable Accounts'
        elif data['form']['result_selection']=='supplier':
            return 'Payable Accounts'
        elif data['form']['result_selection']=='customer_supplier':
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

report_sxw.report_sxw('report.account.third_party_ledger', 'res.partner',
        'addons/account/report/third_party_ledger.rml',parser=third_party_ledger,
        header=False)

report_sxw.report_sxw('report.account.third_party_ledger_other', 'res.partner',
        'addons/account/report/third_party_ledger_other.rml',parser=third_party_ledger,
        header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
