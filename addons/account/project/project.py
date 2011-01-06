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
import time
import operator

import netsvc
from osv import fields
from osv import osv

#
# Object definition
#

class account_analytic_account(osv.osv):
    _name = 'account.analytic.account'
    _description = 'Analytic Accounts'
    logger = netsvc.Logger()

    def _credit_calc(self, cr, uid, ids, name, arg, context={}):
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'Entering _credit_calc; ids:%s'%ids)
        if not ids: return {}

        where_date = ''
        if context.get('from_date'):
            where_date += " AND l.date >= %(from_date)s"
        if context.get('to_date'):
            where_date += " AND l.date <= %(to_date)s"

        cr.execute("SELECT a.id, COALESCE(SUM(l.amount), 0) "
                   "FROM account_analytic_account a "
                   "LEFT JOIN account_analytic_line l ON (a.id=l.account_id %s)"
                   " WHERE l.amount < 0 AND a.id IN %%(ids)s "
                   "GROUP BY a.id" % (where_date),
                   dict(context, ids=tuple(ids)))
        r = dict(cr.fetchall())
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  '_credit_calc results: %s'%r)
        for i in ids:
            r.setdefault(i,0.0)
        return r

    def _debit_calc(self, cr, uid, ids, name, arg, context={}):
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'Entering _debit_calc; ids:%s'%ids)
        if not ids: return {}

        where_date = ''
        if context.get('from_date'):
            where_date += " AND l.date >= %(from_date)s"
        if context.get('to_date'):
            where_date += " AND l.date <= %(to_date)s"

        cr.execute("SELECT a.id, COALESCE(SUM(l.amount), 0) "
                   "FROM account_analytic_account a "
                   "LEFT JOIN account_analytic_line l ON (a.id=l.account_id %s)"
                   " WHERE l.amount > 0 AND a.id IN %%(ids)s "
                   "GROUP BY a.id" % (where_date),
                   dict(context, ids=tuple(ids)))
        r = dict(cr.fetchall())
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  '_debut_calc results: %s'%r)
        for i in ids:
            r.setdefault(i,0.0)
        return r

    def _balance_calc(self, cr, uid, ids, name, arg, context={}):
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  'Entering _balance_calc; ids:%s; ids2:%s'%(
                            ids, ids2))

        for i in ids:
            res.setdefault(i,0.0)

        if not ids2:
            return res

        where_date = ''
        if context.get('from_date'):
            where_date += " AND l.date >= %(from_date)s"
        if context.get('to_date'):
            where_date += " AND l.date <= %(to_date)s"

        cr.execute("SELECT a.id, COALESCE(SUM(l.amount),0) "
                   "FROM account_analytic_account a "
                   "LEFT JOIN account_analytic_line l ON (a.id=l.account_id %s)"
                   " WHERE a.id IN %%(ids)s "
                   "GROUP BY a.id" % (where_date),
                   dict(context, ids=tuple(ids2)))

        for account_id, sum in cr.fetchall():
            res[account_id] = sum
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  '_balance_calc, (id, sum): %s'%res)

        cr.execute("SELECT a.id, r.currency_id "
                   "FROM account_analytic_account a "
                   "INNER JOIN res_company r ON (a.company_id = r.id) "
                   "WHERE a.id in %s", (tuple(ids2),))

        currency = dict(cr.fetchall())
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  '_balance_calc currency: %s'%currency)

        res_currency= self.pool.get('res.currency')
        for id in ids:
            if id not in ids2:
                continue
            for child in self.search(cr, uid, [('parent_id', 'child_of', [id])]):
                if child != id:
                    res.setdefault(id, 0.0)
                    if  currency[child]<>currency[id]:
                        res[id] += res_currency.compute(cr, uid, currency[child], currency[id], res.get(child, 0.0), context=context)
                    else:
                        res[id] += res.get(child, 0.0)

        cur_obj = res_currency.browse(cr,uid,currency.values(),context)
        cur_obj = dict([(o.id, o) for o in cur_obj])
        for id in ids:
            if id in ids2:
                res[id] = res_currency.round(cr,uid,cur_obj[currency[id]],res.get(id,0.0))

        return dict([(i, res[i]) for i in ids ])

    def _quantity_calc(self, cr, uid, ids, name, arg, context={}):
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  '_quantity_calc ids:%s'%ids)
        #XXX must convert into one uom
        res = {}
        ids2 = self.search(cr, uid, [('parent_id', 'child_of', ids)])

        for i in ids:
            res.setdefault(i,0.0)

        if not ids2:
            return res

        where_date = ''
        if context.get('from_date'):
            where_date += " AND l.date >= %(from_date)s"
        if context.get('to_date'):
            where_date += " AND l.date <= %(to_date)s"

        cr.execute('SELECT a.id, COALESCE(SUM(l.unit_amount), 0) \
                FROM account_analytic_account a \
                    LEFT JOIN account_analytic_line l ON (a.id = l.account_id %s) \
                WHERE a.id IN %%(ids)s GROUP BY a.id'%(where_date),
                   dict(context, ids=tuple(ids2)))

        for account_id, sum in cr.fetchall():
            res[account_id] = sum
        self.logger.notifyChannel('addons.'+self._name, netsvc.LOG_DEBUG,
                                  '_quantity_calc, (id, sum): %s'%res)

        for id in ids:
            if id not in ids2:
                continue
            for child in self.search(cr, uid, [('parent_id', 'child_of', [id])]):
                if child != id:
                    res.setdefault(id, 0.0)
                    res[id] += res.get(child, 0.0)
        return dict([(i, res[i]) for i in ids])

    def name_get(self, cr, uid, ids, context={}):
        if not len(ids):
            return []
        reads = self.read(cr, uid, ids, ['name','parent_id'], context)
        res = []
        for record in reads:
            name = record['name']
            if record['parent_id']:
                name = record['parent_id'][1]+' / '+name
            res.append((record['id'], name))
        return res

    def _complete_name_calc(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = self.name_get(cr, uid, ids)
        return dict(res)

    def _get_company_currency(self, cr, uid, ids, field_name, arg, context={}):
        result = {}
        for rec in self.browse(cr, uid, ids, context):
            result[rec.id] = (rec.company_id.currency_id.id,rec.company_id.currency_id.code) or False
        return result

    _columns = {
        'name' : fields.char('Account Name', size=64, required=True),
        'complete_name': fields.function(_complete_name_calc, method=True, type='char', string='Full Account Name'),
        'code' : fields.char('Account Code', size=24),
        'active' : fields.boolean('Active'),
        'type': fields.selection([('view','View'), ('normal','Normal')], 'Account Type'),
        'description' : fields.text('Description'),
        'parent_id': fields.many2one('account.analytic.account', 'Parent Analytic Account', select=2),
        'child_ids': fields.one2many('account.analytic.account', 'parent_id', 'Child Accounts'),
        'line_ids': fields.one2many('account.analytic.line', 'account_id', 'Analytic Entries'),
        'balance' : fields.function(_balance_calc, method=True, type='float', string='Balance'),
        'debit' : fields.function(_debit_calc, method=True, type='float', string='Debit'),
        'credit' : fields.function(_credit_calc, method=True, type='float', string='Credit'),
        'quantity': fields.function(_quantity_calc, method=True, type='float', string='Quantity'),
        'quantity_max': fields.float('Maximum Quantity'),
        'partner_id' : fields.many2one('res.partner', 'Associated Partner'),
        'contact_id' : fields.many2one('res.partner.address', 'Contact'),
        'user_id' : fields.many2one('res.users', 'Account Manager'),
        'date_start': fields.date('Date Start'),
        'date': fields.date('Date End'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'company_currency_id': fields.function(_get_company_currency, method=True, type='many2one', relation='res.currency', string='Currency'),
        'state': fields.selection([('draft','Draft'), ('open','Open'), ('pending','Pending'), ('close','Close'),], 'State', required=True),
    }

    def _default_company(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            return user.company_id.id
        return self.pool.get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]
    _defaults = {
        'active' : lambda *a : True,
        'type' : lambda *a : 'normal',
        'company_id': _default_company,
        'state' : lambda *a : 'draft',
        'user_id' : lambda self,cr,uid,ctx : uid,
        'partner_id': lambda self,cr, uid, ctx: ctx.get('partner_id', False),
        'contact_id': lambda self,cr, uid, ctx: ctx.get('contact_id', False),
    }

    def check_recursion(self, cr, uid, ids, parent=None):
        return super(account_analytic_account, self).check_recursion(cr, uid, ids, parent=parent)

    _order = 'parent_id desc,code'
    _constraints = [
        (check_recursion, 'Error! You can not create recursive analytic accounts.', ['parent_id'])
    ]

    def create(self, cr, uid, vals, context=None):
        parent_id = vals.get('parent_id', 0)
        if ('code' not in vals or not vals['code']) and not parent_id:
            vals['code'] = self.pool.get('ir.sequence').get(cr, uid, 'account.analytic.account')
        return super(account_analytic_account, self).create(cr, uid, vals, context=context)

    def copy(self, cr, uid, id, default=None, context={}):
        if not default:
            default = {}
        default['code'] = False
        default['line_ids'] = []
        return super(account_analytic_account, self).copy(cr, uid, id, default, context=context)


    def on_change_parent(self, cr, uid, id, parent_id):
        if not parent_id:
            return {}
        parent = self.read(cr, uid, [parent_id], ['partner_id','code'])[0]
        childs = self.search(cr, uid, [('parent_id', '=', parent_id), ('active', 'in', [True, False])])
        numchild = len(childs)
        if parent['partner_id']:
            partner = parent['partner_id'][0]
        else:
            partner = False
        res = {'value' : {'code' : '%s - %03d' % (parent['code'] or '', numchild + 1),}}
        if partner:
            res['value']['partner_id'] = partner
        return res

    def name_search(self, cr, uid, name, args=None, operator='ilike', context=None, limit=80):
        if not args:
            args=[]
        if not context:
            context={}
        account = self.search(cr, uid, [('code', '=', name)]+args, limit=limit, context=context)
        if not account:
            account = self.search(cr, uid, [('name', 'ilike', '%%%s%%' % name)]+args, limit=limit, context=context)
            newacc = account
            while newacc:
                newacc = self.search(cr, uid, [('parent_id', 'in', newacc)]+args, limit=limit, context=context)
                account+=newacc
        return self.name_get(cr, uid, account, context=context)

account_analytic_account()


class account_analytic_journal(osv.osv):
    _name = 'account.analytic.journal'
    _columns = {
        'name' : fields.char('Journal name', size=64, required=True),
        'code' : fields.char('Journal code', size=8),
        'active' : fields.boolean('Active'),
        'type': fields.selection([('sale','Sale'), ('purchase','Purchase'), ('cash','Cash'), ('general','General'), ('situation','Situation')], 'Type', size=32, required=True, help="Gives the type of the analytic journal. When a document (eg: an invoice) needs to create analytic entries, Open ERP will look for a matching journal of the same type."),
        'line_ids' : fields.one2many('account.analytic.line', 'journal_id', 'Lines'),
    }
    _defaults = {
        'active': lambda *a: True,
        'type': lambda *a: 'general',
    }
account_analytic_journal()

class account_journal(osv.osv):
    _inherit="account.journal"

    _columns = {
        'analytic_journal_id':fields.many2one('account.analytic.journal','Analytic Journal'),
    }
account_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
