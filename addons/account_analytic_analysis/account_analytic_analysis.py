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

from osv import osv, fields
from osv.orm import intersect, except_orm
import tools.sql
from tools.translate import _
from decimal_precision import decimal_precision as dp


class account_analytic_account(osv.osv):
    _name = "account.analytic.account"
    _inherit = "account.analytic.account"

    def _analysis_all(self, cr, uid, ids, fields, arg, context=None):
        dp = 2
        res = dict([(i, {}) for i in ids])

        parent_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)], context=context))
        res.update(dict([(i, {}) for i in parent_ids]))
        accounts = self.browse(cr, uid, ids, context=context)

        for f in fields:
            if f == 'user_ids':
                cr.execute('SELECT MAX(id) FROM res_users')
                max_user = cr.fetchone()[0]
                if parent_ids:
                    cr.execute('SELECT DISTINCT("user") FROM account_analytic_analysis_summary_user ' \
                               'WHERE account_id IN %s AND unit_amount <> 0.0', (parent_ids,))
                    result = cr.fetchall()
                else:
                    result = []
                for id in ids:
                    res[id][f] = [int((id * max_user) + x[0]) for x in result]
            elif f == 'month_ids':
                if parent_ids:
                    cr.execute('SELECT DISTINCT(month_id) FROM account_analytic_analysis_summary_month ' \
                               'WHERE account_id IN %s AND unit_amount <> 0.0', (parent_ids,))
                    result = cr.fetchall()
                else:
                    result = []
                for id in ids:
                    res[id][f] = [int(id * 1000000 + int(x[0])) for x in result]
            elif f == 'last_worked_invoiced_date':
                for id in ids:
                    res[id][f] = 0.0
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, MAX(date) \
                            FROM account_analytic_line \
                            WHERE account_id IN %s \
                                AND invoice_id IS NOT NULL \
                            GROUP BY account_analytic_line.account_id;", (parent_ids,))
                    for account_id, sum in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = sum
                for account in accounts:
                    for child in account.child_ids:
                        if res[account.id].get(f, '') < res.get(child.id, {}).get(f, ''):
                            res[account.id][f] = res.get(child.id, {}).get(f, '')
            elif f == 'ca_to_invoice':
                for id in ids:
                    res[id][f] = 0.0
                res2 = {}
                if parent_ids:
                    # Amount uninvoiced hours to invoice at sale price
                    # Warning
                    # This computation doesn't take care of pricelist !
                    # Just consider list_price
                    cr.execute("""SELECT account_analytic_account.id, \
                                COALESCE(SUM (product_template.list_price * \
                                    account_analytic_line.unit_amount * \
                                    ((100-hr_timesheet_invoice_factor.factor)/100)), 0.0) \
                                    AS ca_to_invoice \
                            FROM product_template \
                            JOIN product_product \
                                ON product_template.id = product_product.product_tmpl_id \
                            JOIN account_analytic_line \
                                ON account_analytic_line.product_id = product_product.id \
                            JOIN account_analytic_journal \
                                ON account_analytic_line.journal_id = account_analytic_journal.id \
                            JOIN account_analytic_account \
                                ON account_analytic_account.id = account_analytic_line.account_id \
                            JOIN hr_timesheet_invoice_factor \
                                ON hr_timesheet_invoice_factor.id = account_analytic_account.to_invoice \
                            WHERE account_analytic_account.id IN %s \
                                AND account_analytic_line.invoice_id IS NULL \
                                AND account_analytic_line.to_invoice IS NOT NULL \
                                AND account_analytic_journal.type IN ('purchase','general') \
                            GROUP BY account_analytic_account.id;""", (parent_ids,))
                    for account_id, sum in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = round(sum, dp)

                for account in accounts:
                    #res.setdefault(account.id, 0.0)
                    res2.setdefault(account.id, 0.0)
                    for child in account.child_ids:
                        if child.id != account.id:
                            res[account.id][f] += res.get(child.id, {}).get(f, 0.0)
                            res2[account.id] += res2.get(child.id, 0.0)
                # sum both result on account_id
                for id in ids:
                    res[id][f] = round(res.get(id, {}).get(f, 0.0), dp) + round(res2.get(id, 0.0), 2)
            elif f == 'last_invoice_date':
                for id in ids:
                    res[id][f] = ''
                if parent_ids:
                    cr.execute ("SELECT account_analytic_line.account_id, \
                                DATE(MAX(account_invoice.date_invoice)) \
                            FROM account_analytic_line \
                            JOIN account_invoice \
                                ON account_analytic_line.invoice_id = account_invoice.id \
                            WHERE account_analytic_line.account_id IN %s \
                                AND account_analytic_line.invoice_id IS NOT NULL \
                            GROUP BY account_analytic_line.account_id",(parent_ids,))
                    for account_id, lid in cr.fetchall():
                        res[account_id][f] = lid
                for account in accounts:
                    for child in account.child_ids:
                        if res[account.id][f] < res.get(child.id, {}).get(f, ''):
                            res[account.id][f] = res.get(child.id, {}).get(f, '')
            elif f == 'last_worked_date':
                for id in ids:
                    res[id][f] = ''
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, MAX(date) \
                            FROM account_analytic_line \
                            WHERE account_id IN %s \
                                AND invoice_id IS NULL \
                            GROUP BY account_analytic_line.account_id",(parent_ids,))
                    for account_id, lwd in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = lwd
                for account in accounts:
                    for child in account.child_ids:
                        if res[account.id][f] < res.get(child.id, {}).get(f, ''):
                            res[account.id][f] = res.get(child.id, {}).get(f, '')
            elif f == 'hours_qtt_non_invoiced':
                for id in ids:
                    res[id][f] = 0.0
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, COALESCE(SUM(unit_amount), 0.0) \
                            FROM account_analytic_line \
                            JOIN account_analytic_journal \
                                ON account_analytic_line.journal_id = account_analytic_journal.id \
                            WHERE account_analytic_line.account_id IN %s \
                                AND account_analytic_journal.type='general' \
                                AND invoice_id IS NULL \
                                AND to_invoice IS NOT NULL \
                            GROUP BY account_analytic_line.account_id;",(parent_ids,))
                    for account_id, sua in cr.fetchall():
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = round(sua, dp)
                for account in accounts:
                    for child in account.child_ids:
                        if account.id != child.id:
                            res[account.id][f] += res.get(child.id, {}).get(f, 0.0)
                for id in ids:
                    res[id][f] = round(res[id][f], dp)
            elif f == 'hours_quantity':
                for id in ids:
                    res[id][f] = 0.0
                if parent_ids:
                    cr.execute("SELECT account_analytic_line.account_id, COALESCE(SUM(unit_amount), 0.0) \
                            FROM account_analytic_line \
                            JOIN account_analytic_journal \
                                ON account_analytic_line.journal_id = account_analytic_journal.id \
                            WHERE account_analytic_line.account_id IN %s \
                                AND account_analytic_journal.type='general' \
                            GROUP BY account_analytic_line.account_id",(parent_ids,))
                    ff =  cr.fetchall()
                    for account_id, hq in ff:
                        if account_id not in res:
                            res[account_id] = {}
                        res[account_id][f] = round(hq, dp)
                for account in accounts:
                    for child in account.child_ids:
                        if account.id != child.id:
                            if account.id not in res:
                                res[account.id] = {f: 0.0}
                            res[account.id][f] += res.get(child.id, {}).get(f, 0.0)
                for id in ids:
                    res[id][f] = round(res[id][f], dp)
            elif f == 'ca_theorical':
                # TODO Take care of pricelist and purchase !
                for id in ids:
                    res[id][f] = 0.0
                res2 = {}
                # Warning
                # This computation doesn't take care of pricelist !
                # Just consider list_price
                if parent_ids:
                    cr.execute("""SELECT account_analytic_line.account_id AS account_id, \
                                COALESCE(SUM((account_analytic_line.unit_amount * pt.list_price) \
                                    - (account_analytic_line.unit_amount * pt.list_price \
                                        * hr.factor)), 0.0) AS somme
                            FROM account_analytic_line \
                            LEFT JOIN account_analytic_journal \
                                ON (account_analytic_line.journal_id = account_analytic_journal.id) \
                            JOIN product_product pp \
                                ON (account_analytic_line.product_id = pp.id) \
                            JOIN product_template pt \
                                ON (pp.product_tmpl_id = pt.id) \
                            JOIN account_analytic_account a \
                                ON (a.id=account_analytic_line.account_id) \
                            JOIN hr_timesheet_invoice_factor hr \
                                ON (hr.id=a.to_invoice) \
                        WHERE account_analytic_line.account_id IN %s \
                            AND a.to_invoice IS NOT NULL \
                            AND account_analytic_journal.type IN ('purchase', 'general')
                        GROUP BY account_analytic_line.account_id""",(parent_ids,))
                    for account_id, sum in cr.fetchall():
                        res2[account_id] = round(sum, dp)

                for account in accounts:
                    res2.setdefault(account.id, 0.0)
                    for child in account.child_ids:
                        if account.id != child.id:
                            if account.id not in res:
                                res[account.id] = {f: 0.0}
                            res[account.id][f] += res.get(child.id, {}).get(f, 0.0)
                            res[account.id][f] += res2.get(child.id, 0.0)

                # sum both result on account_id
                for id in ids:
                    res[id][f] = round(res[id][f], dp) + round(res2.get(id, 0.0), dp)

        return res

    def _ca_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        res_final = {}
        child_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)], context=context))
        for i in child_ids:
            res[i] =  {}
            for n in [name]:
                res[i][n] = 0.0
        if not child_ids:
            return res

        if child_ids:
            cr.execute("SELECT account_analytic_line.account_id, COALESCE(SUM(amount), 0.0) \
                    FROM account_analytic_line \
                    JOIN account_analytic_journal \
                        ON account_analytic_line.journal_id = account_analytic_journal.id  \
                    WHERE account_analytic_line.account_id IN %s \
                        AND account_analytic_journal.type = 'sale' \
                    GROUP BY account_analytic_line.account_id", (child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id][name] = round(sum,2)
        data = self._compute_level_tree(cr, uid, ids, child_ids, res, [name], context=context)
        for i in data:
            res_final[i] = data[i][name]
        return res_final

    def _total_cost_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        res_final = {}
        child_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)], context=context))

        for i in child_ids:
            res[i] =  {}
            for n in [name]:
                res[i][n] = 0.0
        if not child_ids:
            return res

        if child_ids:
            cr.execute("""SELECT account_analytic_line.account_id, COALESCE(SUM(amount), 0.0) \
                    FROM account_analytic_line \
                    JOIN account_analytic_journal \
                        ON account_analytic_line.journal_id = account_analytic_journal.id \
                    WHERE account_analytic_line.account_id IN %s \
                        AND amount<0 \
                    GROUP BY account_analytic_line.account_id""",(child_ids,))
            for account_id, sum in cr.fetchall():
                res[account_id][name] = round(sum,2)
        data = self._compute_level_tree(cr, uid, ids, child_ids, res, [name], context)
        for i in data:
            res_final[i] = data[i][name]
        return res_final

    def _remaining_hours_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.quantity_max != 0:
                res[account.id] = account.quantity_max - account.hours_quantity
            else:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _hours_qtt_invoiced_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = account.hours_quantity - account.hours_qtt_non_invoiced
            if res[account.id] < 0:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _revenue_per_hour_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.hours_qtt_invoiced == 0:
                res[account.id]=0.0
            else:
                res[account.id] = account.ca_invoiced / account.hours_qtt_invoiced
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _real_margin_rate_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.ca_invoiced == 0:
                res[account.id]=0.0
            elif account.total_cost != 0.0:
                res[account.id] = -(account.real_margin / account.total_cost) * 100
            else:
                res[account.id] = 0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _remaining_ca_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            if account.amount_max != 0:
                res[account.id] = account.amount_max - account.ca_invoiced
            else:
                res[account.id]=0.0
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _real_margin_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = account.ca_invoiced + account.total_cost
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    def _theorical_margin_calc(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for account in self.browse(cr, uid, ids, context=context):
            res[account.id] = account.ca_theorical + account.total_cost
        for id in ids:
            res[id] = round(res.get(id, 0.0),2)
        return res

    _columns ={
        'ca_invoiced': fields.function(_ca_invoiced_calc, method=True, type='float', string='Invoiced Amount',
            help="Total customer invoiced amount for this account.",
            digits_compute=dp.get_precision('Account')),
        'total_cost': fields.function(_total_cost_calc, method=True, type='float', string='Total Costs',
            help="Total of costs for this account. It includes real costs (from invoices) and indirect costs, like time spent on timesheets.",
            digits_compute=dp.get_precision('Account')),
        'ca_to_invoice': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='float', string='Uninvoiced Amount',
            help="If invoice from analytic account, the remaining amount you can invoice to the customer based on the total costs.",
            digits_compute=dp.get_precision('Account')),
        'ca_theorical': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='float', string='Theoretical Revenue',
            help="Based on the costs you had on the project, what would have been the revenue if all these costs have been invoiced at the normal sale price provided by the pricelist.",
            digits_compute=dp.get_precision('Account')),
        'hours_quantity': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='float', string='Hours Tot',
            help="Number of hours you spent on the analytic account (from timesheet). It computes on all journal of type 'general'."),
        'last_invoice_date': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='date', string='Last Invoice Date',
            help="If invoice from the costs, this is the date of the latest invoiced."),
        'last_worked_invoiced_date': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='date', string='Date of Last Invoiced Cost',
            help="If invoice from the costs, this is the date of the latest work or cost that have been invoiced."),
        'last_worked_date': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='date', string='Date of Last Cost/Work',
            help="Date of the latest work done on this account."),
        'hours_qtt_non_invoiced': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='float', string='Uninvoiced Hours',
            help="Number of hours (from journal of type 'general') that can be invoiced if you invoice based on analytic account."),
        'hours_qtt_invoiced': fields.function(_hours_qtt_invoiced_calc, method=True, type='float', string='Invoiced Hours',
            help="Number of hours that can be invoiced plus those that already have been invoiced."),
        'remaining_hours': fields.function(_remaining_hours_calc, method=True, type='float', string='Remaining Hours',
            help="Computed using the formula: Maximum Quantity - Hours Tot."),
        'remaining_ca': fields.function(_remaining_ca_calc, method=True, type='float', string='Remaining Revenue',
            help="Computed using the formula: Max Invoice Price - Invoiced Amount.",
            digits_compute=dp.get_precision('Account')),
        'revenue_per_hour': fields.function(_revenue_per_hour_calc, method=True, type='float', string='Revenue per Hours (real)',
            help="Computed using the formula: Invoiced Amount / Hours Tot.",
            digits_compute=dp.get_precision('Account')),
        'real_margin': fields.function(_real_margin_calc, method=True, type='float', string='Real Margin',
            help="Computed using the formula: Invoiced Amount - Total Costs.",
            digits_compute=dp.get_precision('Account')),
        'theorical_margin': fields.function(_theorical_margin_calc, method=True, type='float', string='Theoretical Margin',
            help="Computed using the formula: Theorial Revenue - Total Costs",
            digits_compute=dp.get_precision('Account')),
        'real_margin_rate': fields.function(_real_margin_rate_calc, method=True, type='float', string='Real Margin Rate (%)',
            help="Computes using the formula: (Real Margin / Total Costs) * 100.",
            digits_compute=dp.get_precision('Account')),
        'month_ids': fields.function(_analysis_all, method=True, multi='analytic_analysis', type='many2many', relation='account_analytic_analysis.summary.month', string='Month'),
        'user_ids': fields.function(_analysis_all, method=True, multi='analytic_analysis', type="many2many", relation='account_analytic_analysis.summary.user', string='User'),
    }

account_analytic_account()

class account_analytic_account_summary_user(osv.osv):
    _name = "account_analytic_analysis.summary.user"
    _description = "Hours Summary by User"
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
        parent_ids = tuple(account_obj.search(cr, uid, [('parent_id', 'child_of', account_ids)], context=context))
        if parent_ids:
            cr.execute('SELECT id, unit_amount ' \
                    'FROM account_analytic_analysis_summary_user ' \
                    'WHERE account_id IN %s ' \
                        'AND "user" IN %s',(parent_ids, tuple(user_ids),))
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
        'user': fields.many2one('res.users', 'User'),
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
        if context is None:
            context = {}
        if not ids:
            return []

        if fields is None:
            fields = self._columns.keys()
        res_trans_obj = self.pool.get('ir.translation')

        # construct a clause for the rules:
        d1, d2, tables = self.pool.get('ir.rule').domain_get(cr, user, self._name, 'read', context=context)

        # all inherited fields + all non inherited fields for which the attribute whose name is in load is True
        fields_pre = filter(lambda x: x in self._columns and getattr(self._columns[x],'_classic_write'), fields) + self._inherits.values()
        res = []
        cr.execute('SELECT MAX(id) FROM res_users')
        max_user = cr.fetchone()[0]
        if fields_pre:
            fields_pre2 = map(lambda x: (x in ('create_date', 'write_date')) and ('date_trunc(\'second\', '+x+') as '+x) or '"'+x+'"', fields_pre)
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = ids[i:i+cr.IN_MAX]
                if d1:
                    cr.execute('SELECT %s FROM \"%s\" WHERE id IN (%s) ' \
                            'AND account_id IN (%s) ' \
                            'AND "user" IN (%s) AND %s ORDER BY %s' % \
                            (','.join(fields_pre2 + ['id']), self._table,
                                ','.join([str(x) for x in sub_ids]),
                                ','.join([str(x/max_user - (x%max_user == 0 and 1 or 0)) for x in sub_ids]),
                                ','.join([str(x-((x/max_user - (x%max_user == 0 and 1 or 0)) *max_user)) for x in sub_ids]), d1,
                                self._order),d2)
                    if not cr.rowcount == len({}.fromkeys(sub_ids)):
                        raise except_orm(_('AccessError'),
                                _('You try to bypass an access rule (Document type: %s).') % self._description)
                else:
                    cr.execute('SELECT %s FROM \"%s\" WHERE id IN (%s) ' \
                            'AND account_id IN (%s) ' \
                            'AND "user" IN (%s) ORDER BY %s' % \
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
                res_trans = res_trans_obj._get_ids(cr, user, self._name+','+f, 'model', context.get('lang', False) or 'en_US', ids)
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

    def _unit_amount(self, cr, uid, ids, name, arg, context=None):
        res = {}
        account_obj = self.pool.get('account.analytic.account')
        account_ids = [int(str(int(x))[:-6]) for x in ids]
        month_ids = [int(str(int(x))[-6:]) for x in ids]
        parent_ids = tuple(account_obj.search(cr, uid, [('parent_id', 'child_of', account_ids)], context=context))
        if parent_ids:
            cr.execute('SELECT id, unit_amount ' \
                    'FROM account_analytic_analysis_summary_month ' \
                    'WHERE account_id IN %s ' \
                        'AND month_id IN %s ',(parent_ids, tuple(month_ids),))
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
        'account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'unit_amount': fields.function(_unit_amount, method=True, type='float', string='Total Time'),
        'month': fields.char('Month', size=32, readonly=True),
    }

    def init(self, cr):
        tools.sql.drop_view_if_exists(cr, 'account_analytic_analysis_summary_month')
        cr.execute('CREATE VIEW account_analytic_analysis_summary_month AS (' \
                'SELECT ' \
                    '(TO_NUMBER(TO_CHAR(d.month, \'YYYYMM\'), \'999999\') + (d.account_id  * 1000000::bigint))::bigint AS id, ' \
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
        if context is None:
            context = {}
        if not ids:
            return []

        if fields is None:
            fields = self._columns.keys()
        res_trans_obj = self.pool.get('ir.translation')
        # construct a clause for the rules:
        d1, d2, tables= self.pool.get('ir.rule').domain_get(cr, user, self._name)

        # all inherited fields + all non inherited fields for which the attribute whose name is in load is True
        fields_pre = filter(lambda x: x in self._columns and getattr(self._columns[x],'_classic_write'), fields) + self._inherits.values()
        res = []
        if fields_pre:
            fields_pre2 = map(lambda x: (x in ('create_date', 'write_date')) and ('date_trunc(\'second\', '+x+') as '+x) or '"'+x+'"', fields_pre)
            for i in range(0, len(ids), cr.IN_MAX):
                sub_ids = ids[i:i+cr.IN_MAX]
                if d1:
                    cr.execute('SELECT %s FROM \"%s\" WHERE id IN (%s) ' \
                            'AND account_id IN (%s) ' \
                            'AND month_id IN (%s) AND %s ORDER BY %s' % \
                            (','.join(fields_pre2 + ['id']), self._table,
                                ','.join([str(x) for x in sub_ids]),
                                ','.join([str(x)[:-6] for x in sub_ids]),
                                ','.join([str(x)[-6:] for x in sub_ids]), d1,
                                self._order),d2)
                    if not cr.rowcount == len({}.fromkeys(sub_ids)):
                        raise except_orm(_('AccessError'),
                                _('You try to bypass an access rule (Document type: %s).') % self._description)
                else:
                    cr.execute('SELECT %s FROM \"%s\" WHERE id IN (%s) ' \
                            'AND account_id IN (%s) ' \
                            'AND month_id IN (%s) ORDER BY %s' % \
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
                res_trans = res_trans_obj._get_ids(cr, user, self._name+','+f, 'model', context.get('lang', False) or 'en_US', ids)
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
