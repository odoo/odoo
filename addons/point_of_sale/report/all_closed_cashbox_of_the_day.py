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
from openerp.report import report_sxw

class all_closed_cashbox_of_the_day(report_sxw.rml_parse):
    #TOFIX: sql injection problem: SQL Request must be pass from sql injection...
    def __init__(self, cr, uid, name, context):
        super(all_closed_cashbox_of_the_day, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
                'time': time,
                'get_data':self._get_data,
                'get_bal':self._get_bal,
                'get_lines':self._get_lines,
                'get_partner':self._get_partner,
                'get_net_total':self._get_net_total,
                'get_user':self._get_user,
                'get_sub_total':self._get_sub_total,
                'get_net_total_starting':self._get_net_total_starting,
        })

    def _get_user(self, line_ids):
        sql = "select name from res_users where id = %d"%(line_ids['create_uid'])
        self.cr.execute(sql)
        user = self.cr.fetchone()
        return user[0]

    def _get_data(self, user):
        data = {}
        sql = """ SELECT abs.journal_id,abs.id,abs.date,abs.closing_date,abs.name as statement,aj.name as journal,ap.name as period,ru.name as user,rc.name as company,
                       abs.state,abs.balance_end_real FROM account_bank_statement as abs
                       LEFT JOIN account_journal as aj ON aj.id = abs.journal_id
                       LEFT JOIN account_period as ap ON ap.id = abs.period_id
                       LEFT JOIN res_users as ru ON ru.id = abs.user_id
                       LEFT JOIN res_company as rc ON rc.id = abs.company_id
                       WHERE to_char(date_trunc('day',abs.date),'YYYY-MM-DD')::date  = current_date and abs.state IN ('confirm','open') and abs.user_id = %d"""%(user.id)
        self.cr.execute(sql)
        data = self.cr.dictfetchall()
        return data

    def _get_lines(self, statement):
        data = {}
        sql = """ select absl.* from account_bank_statement_line as absl, account_bank_statement as abs
                           where absl.statement_id = abs.id and abs.id = %d"""%(statement['id'])
        self.cr.execute(sql)
        data = self.cr.dictfetchall()
        return data

    def _get_bal(self, data):
        res = {}
        sql =""" select sum(pieces*number) as bal from account_cashbox_line where starting_id = %d """%(data['id'])
        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        if res:
            return res[0]['bal']
        else:
            return 0

    def _get_sub_total(self, user, data, date):
        res={}
        self.cr.execute(""" select sum(absl.amount) from account_bank_statement as abs
                            LEFT JOIN account_bank_statement_line as absl ON abs.id = absl.statement_id
                            WHERE abs.journal_id = %d
                            and abs.state IN ('confirm','open')
                            and abs.date = '%s'
                            and abs.user_id = %d
                            """%(data,date,user.id))
        res = self.cr.fetchall()
        if res[0][0]:
            return res[0][0]
        else:
            return False

    def _get_partner(self, statement):
        res = {}
        if statement['pos_statement_id']:
            sql =""" select rp.name  from account_bank_statement_line as absl,res_partner as rp
                                            where absl.partner_id = rp.id
                                            and absl.pos_statement_id = %d"""%(statement['pos_statement_id'])
            self.cr.execute(sql)
            res = self.cr.dictfetchall() or {}
            return res and res[0]['name']
        else:
            return 0.00

    def _get_net_total_starting(self, user):
        lst = []
        res={}
        total_ending_bal = 0.0
        total_starting_bal = 0.0
        sql = """ SELECT abs.id,abs.balance_end_real as net_total FROM account_bank_statement as abs
                    WHERE to_char(date_trunc('day',abs.date),'YYYY-MM-DD')::date  = current_date
                    and abs.state IN ('confirm','open')
                    and abs.user_id = %d"""%(user.id)
        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        for r in res:
            total_ending_bal += (r['net_total'] or 0.0)
            sql1 =""" select sum(pieces*number) as bal from account_cashbox_line where starting_id = %d"""%(r['id'])
            self.cr.execute(sql1)
            data = self.cr.dictfetchall()
            if data[0]['bal']:
                total_starting_bal += data[0]['bal']
        lst.append(total_ending_bal)
        lst.append(total_starting_bal)
        return lst

    def _get_net_total(self, user):
        res={}
        sql = """select sum(absl.amount) as net_total from account_bank_statement as abs
                    LEFT JOIN account_bank_statement_line as absl ON abs.id = absl.statement_id
                    where abs.state IN ('confirm','open') and abs.user_id = %d
                    and to_char(date_trunc('day',abs.date),'YYYY-MM-DD')::date  = current_date """%(user.id)

        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        return res[0]['net_total'] or 0.0

report_sxw.report_sxw('report.all.closed.cashbox.of.the.day', 'account.bank.statement', 'addons/point_of_sale/report/all_closed_cashbox_of_the_day.rml', parser=all_closed_cashbox_of_the_day,header='internal')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
