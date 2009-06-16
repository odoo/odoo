# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 CamptoCamp
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
from mx.DateTime import *
from report import report_sxw
import xml
import rml_parse
import pooler

class general_ledger_landscape(rml_parse.rml_parse):
    _name = 'report.account.general.ledger_landscape'


    def set_context(self, objects, data, ids, report_type = None):
        ##
        self.borne_date = self.get_min_date(data['form'])
        ##
        new_ids = []
        if (data['model'] == 'account.account'):
            new_ids = ids
        else:
            new_ids.append(data['form']['Account_list'])

            objects = self.pool.get('account.account').browse(self.cr, self.uid, new_ids)

        super(general_ledger_landscape, self).set_context(objects, data, new_ids,report_type)

    def __init__(self, cr, uid, name, context):
        super(general_ledger_landscape, self).__init__(cr, uid, name, context)
        self.date_borne = {}
        self.query = ""
        self.child_ids = ""
        self.tot_currency = 0.0
        self.period_sql = ""
        self.sold_accounts = {}
        self.localcontext.update( {
            'time': time,
            'lines': self.lines,
            'sum_debit_account': self._sum_debit_account,
            'sum_credit_account': self._sum_credit_account,
            'sum_solde_account': self._sum_solde_account,
            'sum_debit': self._sum_debit,
            'sum_credit': self._sum_credit,
            'sum_solde': self._sum_solde,
            'get_children_accounts': self.get_children_accounts,
            'sum_currency_amount_account': self._sum_currency_amount_account
        })
        self.context = context
    def _calc_contrepartie(self,cr,uid,ids, context={}):
        result = {}
            #for id in ids:
        #    result.setdefault(id, False)

        for account_line in self.pool.get('account.move.line').browse(cr, uid, ids, context):
            # For avoid long text in the field we will limit it to 5 lines
            #
            #
            #
            result[account_line.id] = ' '
            num_id_move = str(account_line.move_id.id)
            num_id_line = str(account_line.id)
            account_id = str(account_line.account_id.id)
            # search the basic account
            # We have the account ID we will search all account move line from now until this time
            # We are in the case of we are on the top of the account move Line
            cr.execute('SELECT distinct(ac.code) as code_rest,ac.name as name_rest from account_account AS ac, account_move_line mv\
                    where ac.id = mv.account_id and mv.move_id = ' + num_id_move +' and mv.account_id <> ' + account_id )
            res_mv = cr.dictfetchall()
            # we need a result more than 2 line to make the test so we will made the the on 1 because we have exclude the current line
            if (len(res_mv) >=1):
                concat = ''
                rup_id = 0
                for move_rest in res_mv:
                    concat = concat + move_rest['code_rest'] + '|'
                    result[account_line.id] = concat
                    if rup_id >5:
                        # we need to stop the computing and to escape but before we will add "..."
                        result[account_line.id] = concat + '...'
                        break
                    rup_id+=1
        return result

    def get_min_date(self,form):

        ## Get max born from account_fiscal year
        #
        sql = """ select min(fy.date_start) as start_date,max(fy.date_stop) as stop_date from account_fiscalyear
              As fy where fy.state <> 'close'
            """
        self.cr.execute(sql)
        res = self.cr.dictfetchall()
        borne_min = res[0]['start_date']
        borne_max = res[0]['stop_date']
        if form['state'] == 'byperiod':
            ## This function will return the most aged date
            periods = form['periods'][0][2]
            if not periods:
                sql = """
                    Select min(p.date_start) as start_date,max(p.date_stop) as stop_date from account_period as p where p.fiscalyear_id = """ + str(form['fiscalyear'])   + """
                    """
            else:
                periods_id = ','.join(map(str, periods))
                sql = """
                    Select min(p.date_start) as start_date,max(p.date_stop) as stop_date from account_period as p where p.id in ( """ + periods_id   + """)
                    """
            self.cr.execute(sql)
            res = self.cr.dictfetchall()
            borne_min = res[0]['start_date']
            borne_max = res[0]['stop_date']
        elif form['state'] == 'bydate':
            borne_min = form['date_from']
            borne_max = form['date_to']
        elif form['state'] == 'all':
            periods = form['periods'][0][2]
            if not periods:
                sql = """
                    Select min(p.date_start) as start_date,max(p.date_stop) as stop_date from account_period as p where p.fiscalyear_id = """ + str(form['fiscalyear'])   + """
                    """
            else:
                periods_id = ','.join(map(str, periods))
                sql = """
                    Select min(p.date_start) as start_date,max(p.date_stop) as stop_date from account_period as p where p.id in ( """ + periods_id   + """)
                    """
            self.cr.execute(sql)
            res = self.cr.dictfetchall()
            period_min = res[0]['start_date']
            period_max = res[0]['stop_date']
            date_min = form['date_from']
            date_max = form['date_to']
            if period_min<date_min:
                borne_min = period_min
            else :
                borne_min = date_min
            if date_max<period_max:
                borne_max = period_max
            else :
                borne_max = date_max
        elif form['state'] == 'none':
            sql = """
                    SELECT min(date) as start_date,max(date) as stop_date FROM account_move_line """
            self.cr.execute(sql)
            res = self.cr.dictfetchall()
            borne_min = res[0]['start_date']
            borne_max = res[0]['stop_date']
        self.date_borne = {
            'min_date': borne_min,
            'max_date': borne_max,
            }
        return self.date_borne




    def get_children_accounts(self, account, form):

        print self.ids
        self.child_ids = self.pool.get('account.account').search(self.cr, self.uid,
            [('parent_id', 'child_of', self.ids)])
#
        res = []
        ctx = self.context.copy()
        ## We will make the test for period or date
        ## We will now make the test
        #
        if form.has_key('fiscalyear'):
            ctx['fiscalyear'] = form['fiscalyear']
            ctx['periods'] = form['periods'][0][2]
        else:
            ctx['date_from'] = form['date_from']
            ctx['date_to'] = form['date_to']
        ##

        #
        self.query = self.pool.get('account.move.line')._query_get(self.cr, self.uid, context=ctx)
        if account and account.child_consol_ids: # add ids of consolidated childs also of selected account
            ctx['consolidate_childs'] = True
            ctx['account_id'] = account.id
        ids_acc = self.pool.get('account.account').search(self.cr, self.uid,[('parent_id', 'child_of', [account.id])], context=ctx)
        for child_id in ids_acc:
            child_account = self.pool.get('account.account').browse(self.cr, self.uid, child_id)
            sold_account = self._sum_solde_account(child_account,form)
            self.sold_accounts[child_account.id] = sold_account
            if form['display_account'] == 'bal_mouvement':
                if child_account.type != 'view' \
                and len(self.pool.get('account.move.line').search(self.cr, self.uid,
                    [('account_id','=',child_account.id)],
                    context=ctx)) <> 0 :
                    res.append(child_account)
            elif form['display_account'] == 'bal_solde':
                if child_account.type != 'view' \
                and len(self.pool.get('account.move.line').search(self.cr, self.uid,
                    [('account_id','=',child_account.id)],
                    context=ctx)) <> 0 :
                    if ( sold_account <> 0.0):
                        res.append(child_account)
            else:
                if child_account.type != 'view' \
                and len(self.pool.get('account.move.line').search(self.cr, self.uid,
                    [('account_id','>=',child_account.id)],
                    context=ctx)) <> 0 :
                    res.append(child_account)
        ##
        if not len(res):

            return [account]
        else:
            ## We will now compute solde initiaux
            for move in res:
                SOLDEINIT = "SELECT sum(l.debit) AS sum_debit, sum(l.credit) AS sum_credit FROM account_move_line l WHERE l.account_id = " + str(move.id) +  " AND l.date < '" + self.borne_date['max_date'] + "'" +  " AND l.date > '" + self.borne_date['min_date'] + "'"
                self.cr.execute(SOLDEINIT)
                resultat = self.cr.dictfetchall()
                if resultat[0] :
                    if resultat[0]['sum_debit'] == None:
                        sum_debit = 0
                    else:
                        sum_debit = resultat[0]['sum_debit']
                    if resultat[0]['sum_credit'] == None:
                        sum_credit = 0
                    else:
                        sum_credit = resultat[0]['sum_credit']

                    move.init_credit = sum_credit
                    move.init_debit = sum_debit

                else:
                    move.init_credit = 0
                    move.init_debit = 0


        return res

    def lines(self, account, form):
        inv_types = {
                'out_invoice': 'CI: ',
                'in_invoice': 'SI: ',
                'out_refund': 'OR: ',
                'in_refund': 'SR: ',
                }

        if form['sortbydate'] == 'sort_date':
            sorttag = 'l.date'
        else:
            sorttag = 'j.code'
        sql = """
            SELECT l.id, l.date, j.code,c.code AS currency_code,l.amount_currency,l.ref, l.name , l.debit, l.credit, l.period_id
                    FROM account_move_line as l
                       LEFT JOIN res_currency c on (l.currency_id=c.id)
                          JOIN account_journal j on (l.journal_id=j.id)
                             AND account_id = %%s
                             AND %s
                               WHERE l.date<=%%s
                               AND l.date>=%%s
                               ORDER by %s""" % (self.query, sorttag)

        self.cr.execute(sql, (account.id, self.date_borne['max_date'], self.date_borne['min_date'],))

        res = self.cr.dictfetchall()
        sum = 0.0
        account_move_line_obj = pooler.get_pool(self.cr.dbname).get('account.move.line')
        for l in res:
            line = self.pool.get('account.move.line').browse(self.cr, self.uid, l['id'])
            l['move'] = line.move_id.name
            self.cr.execute('Select id from account_invoice where move_id =%s'%(line.move_id.id))
            tmpres = self.cr.dictfetchall()
            if len(tmpres) > 0 :
                inv = self.pool.get('account.invoice').browse(self.cr, self.uid, tmpres[0]['id'])
                l['ref'] = inv_types[inv.type] + ': '+str(inv.number)
            if line.partner_id :
                l['partner'] = line.partner_id.name
            else :
                l['partner'] = ''
            sum = l['debit'] - l ['credit']
#            c = time.strptime(l['date'],"%Y-%m-%d")
#            l['date'] = time.strftime("%d-%m-%Y",c)
            l['progress'] = sum
            l['line_corresp'] = self._calc_contrepartie(self.cr,self.uid,[l['id']])[l['id']]
            # Modification du amount Currency
            if (l['credit'] > 0):
                if l['amount_currency'] != None:
                    l['amount_currency'] = abs(l['amount_currency']) * -1

            #
            if l['amount_currency'] != None:
                self.tot_currency = self.tot_currency + l['amount_currency']
        return res

    def _sum_debit_account(self, account, form):

        self.cr.execute("SELECT sum(debit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id = %s AND %s "%(account.id, self.query))
        ## Add solde init to the result
        #
        sum_debit = self.cr.fetchone()[0] or 0.0
        if form['soldeinit']:
            sum_debit += account.init_debit
        #
        ##
        return sum_debit

    def _sum_credit_account(self, account, form):

        self.cr.execute("SELECT sum(credit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id = %s AND %s "%(account.id,self.query))
        ## Add solde init to the result
        #
        sum_credit = self.cr.fetchone()[0] or 0.0
        if form['soldeinit']:
            sum_credit += account.init_credit
        #
        ##

        return sum_credit

    def _sum_solde_account(self, account, form):
        self.cr.execute("SELECT (sum(debit) - sum(credit)) as tot_solde "\
                "FROM account_move_line l "\
                "WHERE l.account_id = %s AND %s"%(account.id,self.query))
        sum_solde = self.cr.fetchone()[0] or 0.0
        if form['soldeinit']:
            sum_solde += account.init_debit - account.init_credit

        return sum_solde

    def _sum_debit(self, form):
        if not self.ids:
            return 0.0
        self.cr.execute("SELECT sum(debit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id in ("+','.join(map(str, self.child_ids))+") AND "+self.query)
        sum_debit = self.cr.fetchone()[0] or 0.0
        return sum_debit

    def _sum_credit(self, form):
        if not self.ids:
            return 0.0
        self.cr.execute("SELECT sum(credit) "\
                "FROM account_move_line l "\
                "WHERE l.account_id in ("+','.join(map(str, self.child_ids))+") AND "+self.query)
        ## Add solde init to the result
        #
        sum_credit = self.cr.fetchone()[0] or 0.0
        return sum_credit

    def _sum_solde(self, form):
        if not self.ids:
            return 0.0
        self.cr.execute("SELECT (sum(debit) - sum(credit)) as tot_solde "\
                "FROM account_move_line l "\
                "WHERE l.account_id in ("+','.join(map(str, self.child_ids))+") AND "+self.query)
        sum_solde = self.cr.fetchone()[0] or 0.0
        return sum_solde

    def _set_get_account_currency_code(self, account_id):
        self.cr.execute("SELECT c.code as code "\
                "FROM res_currency c,account_account as ac "\
                "WHERE ac.id = %s AND ac.currency_id = c.id"%(account_id))
        result = self.cr.fetchone()
        if result:
            self.account_currency = result[0]
        else:
            self.account_currency = False

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

report_sxw.report_sxw('report.account.general.ledger_landscape', 'account.account', 'addons/account/report/general_ledger_landscape.rml', parser=general_ledger_landscape, header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
