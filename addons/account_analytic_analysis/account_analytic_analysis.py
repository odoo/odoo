# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import operator
from osv import osv, fields
from osv.orm import intersect
import tools.sql 
from tools.translate import _


class account_analytic_account(osv.osv):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

    def _ca_invoiced_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("select account_analytic_line.account_id, COALESCE(sum(amount),0.0) \
                    from account_analytic_line \
                    join account_analytic_journal \
                        on account_analytic_line.journal_id = account_analytic_journal.id  \
                    where account_analytic_line.account_id IN (%s) \
                        and account_analytic_journal.type = 'sale' \
                    group by account_analytic_line.account_id" % acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = round(sum,2)
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if child_id != obj_id:
                    res[obj_id] += res.get(child_id, 0.0)
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _ca_to_invoice_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        res2 = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            # Amount uninvoiced hours to invoice at sale price
            acc_set = ",".join(map(str, ids2))
            cr.execute("""SELECT account_analytic_account.id, \
                        COALESCE(sum (product_template.list_price * \
                            account_analytic_line.unit_amount * \
                            ((100-hr_timesheet_invoice_factor.factor)/100)),0.0) \
                            AS ca_to_invoice \
                    FROM product_template \
                    join product_product \
                        on product_template.id = product_product.product_tmpl_id \
                    JOIN account_analytic_line \
                        on account_analytic_line.product_id = product_product.id \
                    JOIN account_analytic_journal \
                        on account_analytic_line.journal_id = account_analytic_journal.id \
                    JOIN account_analytic_account \
                        on account_analytic_account.id = account_analytic_line.account_id \
                    JOIN hr_timesheet_invoice_factor \
                        on hr_timesheet_invoice_factor.id = account_analytic_account.to_invoice \
                    WHERE account_analytic_account.id IN (%s) \
                        AND account_analytic_line.invoice_id is null \
                        AND account_analytic_line.to_invoice IS NOT NULL \
                        and account_analytic_journal.type in ('purchase','general') \
                    GROUP BY account_analytic_account.id;"""%acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = round(sum,2)

            # Expense amount and purchase invoice
            #acc_set = ",".join(map(str, ids2))
            #cr.execute ("select account_analytic_line.account_id, sum(amount) \
            #        from account_analytic_line \
            #        join account_analytic_journal \
            #            on account_analytic_line.journal_id = account_analytic_journal.id \
            #        where account_analytic_line.account_id IN (%s) \
            #            and account_analytic_journal.type = 'purchase' \
            #        GROUP BY account_analytic_line.account_id;"%acc_set)
            #for account_id, sum in cr.fetchall():
            #    res2[account_id] = round(sum,2)
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            res2.setdefault(obj_id, 0.0)
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if child_id != obj_id:
                    res[obj_id] += res.get(child_id, 0.0)
                    res2[obj_id] += res2.get(child_id, 0.0)
        # sum both result on account_id
        for id in ids:
            res[id] = round(res.get(id, 0.0),2) + round(res2.get(id, 0.0),2)
        return res

    def _hours_qtt_non_invoiced_calc (self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("select account_analytic_line.account_id, COALESCE(sum(unit_amount),0.0) \
                    from account_analytic_line \
                    join account_analytic_journal \
                        on account_analytic_line.journal_id = account_analytic_journal.id \
                    where account_analytic_line.account_id IN (%s) \
                        and account_analytic_journal.type='general' \
                        and invoice_id is null \
                        AND to_invoice IS NOT NULL \
                    GROUP BY account_analytic_line.account_id;"%acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = round(sum,2)
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if child_id != obj_id:
                    res[obj_id] += res.get(child_id, 0.0)
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _hours_quantity_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("select account_analytic_line.account_id,COALESCE(SUM(unit_amount),0.0) \
                    from account_analytic_line \
                    join account_analytic_journal \
                        on account_analytic_line.journal_id = account_analytic_journal.id \
                    where account_analytic_line.account_id IN (%s) \
                        and account_analytic_journal.type='general' \
                    GROUP BY account_analytic_line.account_id"%acc_set)
            ff =  cr.fetchall()
            for account_id, sum in ff:
                res[account_id] = round(sum,2)
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if child_id != obj_id:
                    res[obj_id] += res.get(child_id, 0.0)
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _total_cost_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("""select account_analytic_line.account_id,COALESCE(sum(amount),0.0) \
                    from account_analytic_line \
                    join account_analytic_journal \
                        on account_analytic_line.journal_id = account_analytic_journal.id \
                    where account_analytic_line.account_id IN (%s) \
                        and amount<0 \
                    GROUP BY account_analytic_line.account_id"""%acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = round(sum,2)
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if child_id != obj_id:
                    res[obj_id] += res.get(child_id, 0.0)
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _ca_theorical_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        res2 = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("""select account_analytic_line.account_id as account_id, \
                        COALESCE(sum((account_analytic_line.unit_amount * pt.list_price) \
                            - (account_analytic_line.unit_amount * pt.list_price \
                                * hr.factor)),0.0) as somme
                    from account_analytic_line \
                    left join account_analytic_journal \
                        on (account_analytic_line.journal_id = account_analytic_journal.id) \
                    join product_product pp \
                        on (account_analytic_line.product_id = pp.id) \
                    join product_template pt \
                        on (pp.product_tmpl_id = pt.id) \
                    join account_analytic_account a \
                        on (a.id=account_analytic_line.account_id) \
                    join hr_timesheet_invoice_factor hr \
                        on (hr.id=a.to_invoice) \
                where account_analytic_line.account_id IN (%s) \
                    and a.to_invoice IS NOT NULL \
                    and account_analytic_journal.type in ('purchase','general')
                GROUP BY account_analytic_line.account_id"""%acc_set)
            for account_id, sum in cr.fetchall():
                res2[account_id] = round(sum,2)

        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            res2.setdefault(obj_id, 0.0)
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if child_id != obj_id:
                    res[obj_id] += res.get(child_id, 0.0)
                    res[obj_id] += res2.get(child_id, 0.0)

        # sum both result on account_id
        for id in ids:
            res[id] = round(res.get(id, 0.0),2) + round(res2.get(id, 0.0),2)
        return res

    def _last_worked_date_calc (self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("select account_analytic_line.account_id, max(date) \
                    from account_analytic_line \
                    where account_id IN (%s) \
                        and invoice_id is null \
                    GROUP BY account_analytic_line.account_id" % acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = sum
        for obj_id in ids:
            res.setdefault(obj_id, '')
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if res[obj_id] < res.get(child_id, ''):
                    res[obj_id] = res.get(child_id, '')
        for id in ids:
            res[id] = res.get(id, '')
        return res

    def _last_invoice_date_calc (self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute ("select account_analytic_line.account_id, \
                        date(max(account_invoice.date_invoice)) \
                    from account_analytic_line \
                    join account_invoice \
                        on account_analytic_line.invoice_id = account_invoice.id \
                    where account_analytic_line.account_id IN (%s) \
                        and account_analytic_line.invoice_id is not null \
                    GROUP BY account_analytic_line.account_id"%acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = sum
        for obj_id in ids:
            res.setdefault(obj_id, '')
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if res[obj_id] < res.get(child_id, ''):
                    res[obj_id] = res.get(child_id, '')
        for id in ids:
            res[id] = res.get(id, '')
        return res

    def _last_worked_invoiced_date_calc (self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        if ids2:
            acc_set = ",".join(map(str, ids2))
            cr.execute("select account_analytic_line.account_id, max(date) \
                    from account_analytic_line \
                    where account_id IN (%s) \
                        and invoice_id is not null \
                    GROUP BY account_analytic_line.account_id;"%acc_set)
            for account_id, sum in cr.fetchall():
                res[account_id] = sum
        for obj_id in ids:
            res.setdefault(obj_id, '')
            for child_id in self.search(cr, uid,
                    [('parent_id', 'child_of', [obj_id])]):
                if res[obj_id] < res.get(child_id, ''):
                    res[obj_id] = res.get(child_id, '')
        for id in ids:
            res[id] = res.get(id, '')
        return res

    def _remaining_hours_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            if account.quantity_max <> 0:
                res[account.id] = account.quantity_max - account.hours_quantity
            else:
                res[account.id]=0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _hours_qtt_invoiced_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            res[account.id] = account.hours_quantity - account.hours_qtt_non_invoiced
            if res[account.id] < 0:
                res[account.id]=0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _revenue_per_hour_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            if account.hours_qtt_invoiced == 0:
                res[account.id]=0.0
            else:
                res[account.id] = account.ca_invoiced / account.hours_qtt_invoiced
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _real_margin_rate_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            if account.ca_invoiced == 0:
                res[account.id]=0.0
            elif account.total_cost <> 0.0:
                res[account.id] = -(account.real_margin / account.total_cost) * 100
            else:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _remaining_ca_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            if account.amount_max <> 0:
                res[account.id] = account.amount_max - account.ca_invoiced
            else:
                res[account.id]=0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _real_margin_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            res[account.id] = account.ca_invoiced + account.total_cost
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _theorical_margin_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        for account in self.browse(cr, uid, ids):
            res[account.id] = account.ca_theorical + account.total_cost
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _month(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for id in ids:
            ids2 = self.search(cr, uid, [('parent_id', 'child_of', [id])])
            if ids2:
                cr.execute('SELECT DISTINCT(month_id) FROM account_analytic_analysis_summary_month ' \
                        'WHERE account_id in (' + ','.join([str(x) for x in ids2]) + ') ' \
                            'AND unit_amount <> 0.0')
                res[id] = [int(id * 1000000 + int(x[0])) for x in cr.fetchall()]
            else:
                res[id] = []
        return res

    def _user(self, cr, uid, ids, name, arg, context=None):
        res = {}
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        for id in ids:
            ids2 = self.search(cr, uid, [('parent_id', 'child_of', [id])])
            if ids2:
                cr.execute('SELECT DISTINCT("user") FROM account_analytic_analysis_summary_user ' \
                        'WHERE account_id in (' + ','.join([str(x) for x in ids2]) + ') ' \
                            'AND unit_amount <> 0.0')
                res[id] = [int((id * max_user) + x[0]) for x in cr.fetchall()]
            else:
                res[id] = []   
        return res

    _columns ={
        'ca_invoiced': fields.function(_ca_invoiced_calc, method=True, type='float', string='Invoiced Amount', help="Total customer invoiced amount for this account."),
        'total_cost': fields.function(_total_cost_calc, method=True, type='float', string='Total Costs', help="Total of costs for this account. It includes real costs (from invoices) and indirect costs, like time spent on timesheets."),
        'ca_to_invoice': fields.function(_ca_to_invoice_calc, method=True, type='float', string='Uninvoiced Amount', help="If invoice from analytic account, the remaining amount you can invoice to the customer based on the total costs."),
        'ca_theorical': fields.function(_ca_theorical_calc, method=True, type='float', string='Theorical Revenue', help="Based on the costs you had on the project, what would have been the revenue if all these costs have been invoiced at the normal sale price provided by the pricelist."),
        'hours_quantity': fields.function(_hours_quantity_calc, method=True, type='float', string='Hours Tot', help="Number of hours you spent on the analytic account (from timesheet). It computes on all journal of type 'general'."),
        'last_invoice_date': fields.function(_last_invoice_date_calc, method=True, type='date', string='Last Invoice Date', help="Date of the last invoice created for this analytic account."),
        'last_worked_invoiced_date': fields.function(_last_worked_invoiced_date_calc, method=True, type='date', string='Date of Last Invoiced Cost', help="If invoice from the costs, this is the date of the latest work or cost that have been invoiced."),
        'last_worked_date': fields.function(_last_worked_date_calc, method=True, type='date', string='Date of Last Cost/Work', help="Date of the latest work done on this account."),
        'hours_qtt_non_invoiced': fields.function(_hours_qtt_non_invoiced_calc, method=True, type='float', string='Uninvoiced Hours', help="Number of hours (from journal of type 'general') that can be invoiced if you invoice based on analytic account."),
        'hours_qtt_invoiced': fields.function(_hours_qtt_invoiced_calc, method=True, type='float', string='Invoiced Hours', help="Number of hours that can be invoiced plus those that already have been invoiced."),
        'remaining_hours': fields.function(_remaining_hours_calc, method=True, type='float', string='Remaining Hours', help="Computed using the formula: Maximum Quantity - Hours Tot."),
        'remaining_ca': fields.function(_remaining_ca_calc, method=True, type='float', string='Remaining Revenue', help="Computed using the formula: Max Invoice Price - Invoiced Amount."),
        'revenue_per_hour': fields.function(_revenue_per_hour_calc, method=True, type='float', string='Revenue per Hours (real)', help="Computed using the formula: Invoiced Amount / Hours Tot."),
        'real_margin': fields.function(_real_margin_calc, method=True, type='float', string='Real Margin', help="Computed using the formula: Invoiced Amount - Total Costs."),
        'theorical_margin': fields.function(_theorical_margin_calc, method=True, type='float', string='Theorical Margin', help="Computed using the formula: Theorial Revenue - Total Costs"),
        'real_margin_rate': fields.function(_real_margin_rate_calc, method=True, type='float', string='Real Margin Rate (%)', help="Computes using the formula: (Real Margin / Total Costs) * 100."),
        'month_ids': fields.function(_month, method=True, type='many2many', relation='account_analytic_analysis.summary.month', string='Month'),
        'user_ids': fields.function(_user, method=True, type="many2many", relation='account_analytic_analysis.summary.user', string='User'),
    }
account_analytic_account()

class account_analytic_account_summary_user(osv.osv):
    _name = "account_analytic_analysis.summary.user"
    _description = "Hours summary by user"
    _order='user'
    _auto = False
    _rec_name = 'user'

    def _unit_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        account_obj = self.pool.get('account.analytic.account')
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        account_ids = [int(str(x/max_user - (x%max_user == 0 and 1 or 0))) for x in ids]
        user_ids = [int(str(x-((x/max_user - (x%max_user == 0 and 1 or 0)) *max_user))) for x in ids]
        account_ids2 = account_obj.search(cr, uid, [('parent_id', 'child_of', account_ids)])
        user_set = ','.join([str(x) for x in user_ids])
        if account_ids2:
            acc_set = ','.join([str(x) for x in account_ids2])
            cr.execute('SELECT id, unit_amount ' \
                    'FROM account_analytic_analysis_summary_user ' \
                    'WHERE account_id in (%s) ' \
                        'AND "user" in (%s) ' % (acc_set, user_set))
            for sum_id, unit_amount in cr.fetchall():
                res[sum_id] = unit_amount
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            for child_id in account_obj.search(cr, uid,
                    [('parent_id', 'child_of', [int(str(obj_id/max_user - (obj_id%max_user == 0 and 1 or 0)))])]):
                if child_id != int(str(obj_id/max_user - (obj_id%max_user == 0 and 1 or 0))):
                    res[obj_id] += res.get((child_id * max_user) + obj_id -((obj_id/max_user - (obj_id%max_user == 0 and 1 or 0)) * max_user), 0.0)
        for id in ids:
            res[id] = round(res.get(id, 0.0), 2)
        return res

    _columns = {
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'unit_amount': fields.function(_unit_amount, method=True, type='float',
            string='Total Time'),
        'user' : fields.many2one('res.users', 'User'),
    }
    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'account_analytic_analysis_summary_user')
        cr.execute('CREATE OR REPLACE VIEW account_analytic_analysis_summary_user AS (' \
                'SELECT ' \
                    '(u.account_id * u.max_user) + u."user" AS id, ' \
                    'u.account_id AS account_id, ' \
                    'u."user" AS "user", ' \
                    'COALESCE(SUM(l.unit_amount), 0.0) AS unit_amount ' \
                'FROM ' \
                    '(SELECT ' \
                        'a.id AS account_id, ' \
                        'u1.id AS "user", ' \
                        'MAX(u2.id) AS max_user ' \
                    'FROM ' \
                        'res_users AS u1, ' \
                        'res_users AS u2, ' \
                        'account_analytic_account AS a ' \
                    'GROUP BY u1.id, a.id ' \
                    ') AS u ' \
                'LEFT JOIN ' \
                    '(SELECT ' \
                        'l.account_id AS account_id, ' \
                        'l.user_id AS "user", ' \
                        'SUM(l.unit_amount) AS unit_amount ' \
                    'FROM account_analytic_line AS l, ' \
                        'account_analytic_journal AS j ' \
                    'WHERE (j.type = \'general\') and (j.id=l.journal_id) ' \
                    'GROUP BY l.account_id, l.user_id ' \
                    ') AS l '
                    'ON (' \
                        'u.account_id = l.account_id ' \
                        'AND u."user" = l."user"' \
                    ') ' \
                'GROUP BY u."user", u.account_id, u.max_user' \
                ')')

    def _read_flat(self, cr, user, ids, fields, context=None, load='_classic_read'):
        if not context:
            context={}
        if not ids:
            return []

        if fields==None:
            fields = self._columns.keys()

        # construct a clause for the rules :
        d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)

        # all inherited fields + all non inherited fields for which the attribute whose name is in load is True
        fields_pre = filter(lambda x: x in self._columns and getattr(self._columns[x],'_classic_write'), fields) + self._inherits.values()

        res = []
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        if len(fields_pre) :
            fields_pre2 = map(lambda x: (x in ('create_date', 'write_date')) and ('date_trunc(\'second\', '+x+') as '+x) or '"'+x+'"', fields_pre)
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = ids[i:i+cr.IN_MAX]
                if d1:
                    cr.execute('select %s from \"%s\" where id in (%s) ' \
                            'and account_id in (%s) ' \
                            'and "user" in (%s) and %s order by %s' % \
                            (','.join(fields_pre2 + ['id']), self._table,
                                ','.join([str(x) for x in sub_ids]),
                                ','.join([str(x/max_user - (x%max_user == 0 and 1 or 0)) for x in sub_ids]),
                                ','.join([str(x-((x/max_user - (x%max_user == 0 and 1 or 0)) *max_user)) for x in sub_ids]), d1,
                                self._order),d2)
                    if not cr.rowcount == len({}.fromkeys(sub_ids)):
                        raise except_orm(_('AccessError'),
                                _('You try to bypass an access rule (Document type: %s).') % self._description)
                else:
                    cr.execute('select %s from \"%s\" where id in (%s) ' \
                            'and account_id in (%s) ' \
                            'and "user" in (%s) order by %s' % \
                            (','.join(fields_pre2 + ['id']), self._table,
                                ','.join([str(x) for x in sub_ids]),
                                ','.join([str(x/max_user - (x%max_user == 0 and 1 or 0)) for x in sub_ids]),
                                ','.join([str(x-((x/max_user - (x%max_user == 0 and 1 or 0)) *max_user)) for x in sub_ids]),
                                self._order))
                res.extend(cr.dictfetchall())
        else:
            res = map(lambda x: {'id': x}, ids)

        for f in fields_pre:
            if self._columns[f].translate:
                ids = map(lambda x: x['id'], res)
                res_trans = self.pool.get('ir.translation')._get_ids(cr, user, self._name+','+f, 'model', context.get('lang', False) or 'en_US', ids)
                for r in res:
                    r[f] = res_trans.get(r['id'], False) or r[f]

        for table in self._inherits:
            col = self._inherits[table]
            cols = intersect(self._inherit_fields.keys(), fields)
            if not cols:
                continue
            res2 = self.pool.get(table).read(cr, user, [x[col] for x in res], cols, context, load)

            res3 = {}
            for r in res2:
                res3[r['id']] = r
                del r['id']

            for record in res:
                record.update(res3[record[col]])
                if col not in fields:
                    del record[col]

        # all fields which need to be post-processed by a simple function (symbol_get)
        fields_post = filter(lambda x: x in self._columns and self._columns[x]._symbol_get, fields)
        if fields_post:
            # maybe it would be faster to iterate on the fields then on res, so that we wouldn't need
            # to get the _symbol_get in each occurence
            for r in res:
                for f in fields_post:
                    r[f] = self.columns[f]._symbol_get(r[f])
        ids = map(lambda x: x['id'], res)

        # all non inherited fields for which the attribute whose name is in load is False
        fields_post = filter(lambda x: x in self._columns and not getattr(self._columns[x], load), fields)
        for f in fields_post:
            # get the value of that field for all records/ids
            res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=res)
            for record in res:
                record[f] = res2[record['id']]

        return res

account_analytic_account_summary_user()

class account_analytic_account_summary_month(osv.osv):
    _name = "account_analytic_analysis.summary.month"
    _description = "Hours summary by month"
    _auto = False
    _rec_name = 'month'
#    _order = 'month'

    def _unit_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        account_obj = self.pool.get('account.analytic.account')
        account_ids = [int(str(int(x))[:-6]) for x in ids]
        month_ids = [int(str(int(x))[-6:]) for x in ids]
        account_ids2 = account_obj.search(cr, uid, [('parent_id', 'child_of', account_ids)])
        month_set = ','.join([str(x) for x in month_ids])
        if account_ids2:
            acc_set = ','.join([str(x) for x in account_ids2])
            cr.execute('SELECT id, unit_amount ' \
                    'FROM account_analytic_analysis_summary_month ' \
                    'WHERE account_id in (%s) ' \
                        'AND month_id in (%s) ' % \
                        (acc_set, month_set))
            for sum_id, unit_amount in cr.fetchall():
                res[sum_id] = unit_amount
        for obj_id in ids:
            res.setdefault(obj_id, 0.0)
            for child_id in account_obj.search(cr, uid,
                    [('parent_id', 'child_of', [int(str(int(obj_id))[:-6])])]):
                if child_id != int(str(int(obj_id))[:-6]):
                    res[obj_id] += res.get(int(child_id * 1000000 + int(str(int(obj_id))[-6:])), 0.0)
        for id in ids:
            res[id] = round(res.get(id, 0.0), 2)
        return res

    _columns = {
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account',
            readonly=True),
        'unit_amount': fields.function(_unit_amount, method=True, type='float',
            string='Total Time'),
        'month': fields.char('Month', size=25, readonly=True),
    }

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'account_analytic_analysis_summary_month')
        cr.execute('CREATE VIEW account_analytic_analysis_summary_month AS (' \
                'SELECT ' \
                    '(TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') + (d.account_id  * 1000000))::integer AS id, ' \
                    'd.account_id AS account_id, ' \
                    'TO_CHAR(d.month, \'Mon YYYY\') AS month, ' \
                    'TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') AS month_id, ' \
                    'COALESCE(SUM(l.unit_amount), 0.0) AS unit_amount ' \
                'FROM ' \
                    '(SELECT ' \
                        'd2.account_id, ' \
                        'd2.month ' \
                    'FROM ' \
                        '(SELECT ' \
                            'a.id AS account_id, ' \
                            'l.month AS month ' \
                        'FROM ' \
                            '(SELECT ' \
                                'DATE_TRUNC(\'month\', l.date) AS month ' \
                            'FROM account_analytic_line AS l, ' \
                                'account_analytic_journal AS j ' \
                            'WHERE j.type = \'general\' ' \
                            'GROUP BY DATE_TRUNC(\'month\', l.date) ' \
                            ') AS l, ' \
                            'account_analytic_account AS a ' \
                        'GROUP BY l.month, a.id ' \
                        ') AS d2 ' \
                    'GROUP BY d2.account_id, d2.month ' \
                    ') AS d ' \
                'LEFT JOIN ' \
                    '(SELECT ' \
                        'l.account_id AS account_id, ' \
                        'DATE_TRUNC(\'month\', l.date) AS month, ' \
                        'SUM(l.unit_amount) AS unit_amount ' \
                    'FROM account_analytic_line AS l, ' \
                        'account_analytic_journal AS j ' \
                    'WHERE (j.type = \'general\') and (j.id=l.journal_id) ' \
                    'GROUP BY l.account_id, DATE_TRUNC(\'month\', l.date) ' \
                    ') AS l '
                    'ON (' \
                        'd.account_id = l.account_id ' \
                        'AND d.month = l.month' \
                    ') ' \
                'GROUP BY d.month, d.account_id ' \
                ')')

    def _read_flat(self, cr, user, ids, fields, context=None, load='_classic_read'):
        if not context:
            context={}
        if not ids:
            return []

        if fields==None:
            fields = self._columns.keys()

        # construct a clause for the rules :
        d1, d2 = self.pool.get('ir.rule').domain_get(cr, user, self._name)

        # all inherited fields + all non inherited fields for which the attribute whose name is in load is True
        fields_pre = filter(lambda x: x in self._columns and getattr(self._columns[x],'_classic_write'), fields) + self._inherits.values()

        res = []
        if len(fields_pre) :
            fields_pre2 = map(lambda x: (x in ('create_date', 'write_date')) and ('date_trunc(\'second\', '+x+') as '+x) or '"'+x+'"', fields_pre)
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = ids[i:i+cr.IN_MAX]
                if d1:
                    cr.execute('select %s from \"%s\" where id in (%s) ' \
                            'and account_id in (%s) ' \
                            'and month_id in (%s) and %s order by %s' % \
                            (','.join(fields_pre2 + ['id']), self._table,
                                ','.join([str(x) for x in sub_ids]),
                                ','.join([str(x)[:-6] for x in sub_ids]),
                                ','.join([str(x)[-6:] for x in sub_ids]), d1,
                                self._order),d2)
                    if not cr.rowcount == len({}.fromkeys(sub_ids)):
                        raise except_orm(_('AccessError'),
                                _('You try to bypass an access rule (Document type: %s).') % self._description)
                else:
                    cr.execute('select %s from \"%s\" where id in (%s) ' \
                            'and account_id in (%s) ' \
                            'and month_id in (%s) order by %s' % \
                            (','.join(fields_pre2 + ['id']), self._table,
                                ','.join([str(x) for x in sub_ids]),
                                ','.join([str(x)[:-6] for x in sub_ids]),
                                ','.join([str(x)[-6:] for x in sub_ids]),
                                self._order))
                res.extend(cr.dictfetchall())
        else:
            res = map(lambda x: {'id': x}, ids)

        for f in fields_pre:
            if self._columns[f].translate:
                ids = map(lambda x: x['id'], res)
                res_trans = self.pool.get('ir.translation')._get_ids(cr, user, self._name+','+f, 'model', context.get('lang', False) or 'en_US', ids)
                for r in res:
                    r[f] = res_trans.get(r['id'], False) or r[f]

        for table in self._inherits:
            col = self._inherits[table]
            cols = intersect(self._inherit_fields.keys(), fields)
            if not cols:
                continue
            res2 = self.pool.get(table).read(cr, user, [x[col] for x in res], cols, context, load)

            res3 = {}
            for r in res2:
                res3[r['id']] = r
                del r['id']

            for record in res:
                record.update(res3[record[col]])
                if col not in fields:
                    del record[col]

        # all fields which need to be post-processed by a simple function (symbol_get)
        fields_post = filter(lambda x: x in self._columns and self._columns[x]._symbol_get, fields)
        if fields_post:
            # maybe it would be faster to iterate on the fields then on res, so that we wouldn't need
            # to get the _symbol_get in each occurence
            for r in res:
                for f in fields_post:
                    r[f] = self.columns[f]._symbol_get(r[f])
        ids = map(lambda x: x['id'], res)

        # all non inherited fields for which the attribute whose name is in load is False
        fields_post = filter(lambda x: x in self._columns and not getattr(self._columns[x], load), fields)
        for f in fields_post:
            # get the value of that field for all records/ids
            res2 = self._columns[f].get(cr, self, ids, f, user, context=context, values=res)
            for record in res:
                record[f] = res2[record['id']]

        return res

account_analytic_account_summary_month()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

