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
import netsvc
from osv import fields, osv
import ir

from tools.misc import currency
from tools.translate import _

import mx.DateTime
from mx.DateTime import RelativeDateTime, now, DateTime, localtime

class res_currency(osv.osv):
    def _current_rate(self, cr, uid, ids, name, arg, context={}):
        res={}
        if 'date' in context:
            date=context['date']
        else:
            date=time.strftime('%Y-%m-%d')
        date= date or time.strftime('%Y-%m-%d')
        for id in ids:
            cr.execute("SELECT currency_id, rate FROM res_currency_rate WHERE currency_id = %s AND name <= %s ORDER BY name desc LIMIT 1", (id, date))
            if cr.rowcount:
                id, rate=cr.fetchall()[0]
                res[id]=rate
            else:
                res[id]=0
        return res
    _name = "res.currency"
    _description = "Currency"
    _columns = {
        'name': fields.char('Currency', size=32, required=True),
        'code': fields.char('Code', size=3),
        'rate': fields.function(_current_rate, method=True, string='Current Rate', digits=(12,6),
            help='The rate of the currency to the currency of rate 1'),
        'rate_ids': fields.one2many('res.currency.rate', 'currency_id', 'Rates'),
        'accuracy': fields.integer('Computational Accuracy'),
        'rounding': fields.float('Rounding factor', digits=(12,6)),
        'active': fields.boolean('Active'),
    }
    _defaults = {
        'active': lambda *a: 1,
    }
    _order = "code"

    def round(self, cr, uid, currency, amount):
        if currency.rounding == 0:
            return 0.0
        else:
            return round(amount / currency.rounding,6) * currency.rounding

    def is_zero(self, cr, uid, currency, amount):
        return abs(self.round(cr, uid, currency, amount)) < currency.rounding

    def compute(self, cr, uid, from_currency_id, to_currency_id, from_amount, round=True, context={}, account=None, account_invert=False):
        if not from_currency_id:
            from_currency_id = to_currency_id
        xc=self.browse(cr, uid, [from_currency_id,to_currency_id], context=context)
        from_currency = (xc[0].id == from_currency_id and xc[0]) or xc[1]
        to_currency = (xc[0].id == to_currency_id and xc[0]) or xc[1]
        if from_currency['rate'] == 0 or to_currency['rate'] == 0:
            date = context.get('date', time.strftime('%Y-%m-%d'))
            if from_currency['rate'] == 0:
                code = from_currency.code
            else:
                code = to_currency.code
            raise osv.except_osv(_('Error'), _('No rate found \n' \
                    'for the currency: %s \n' \
                    'at the date: %s') % (code, date))
        rate = to_currency.rate/from_currency.rate
        if account and (account.currency_mode=='average') and account.currency_id:
            q = self.pool.get('account.move.line')._query_get(cr, uid, context=context)
            cr.execute('select sum(debit-credit),sum(amount_currency) from account_move_line l ' \
              'where l.currency_id=%s and l.account_id=%s and '+q, (account.currency_id.id,account.id,))
            tot1,tot2 = cr.fetchone()
            if tot2 and not account_invert:
                rate = float(tot1)/float(tot2)
            elif tot1 and account_invert:
                rate = float(tot2)/float(tot1)
        if to_currency_id==from_currency_id:
            if round:
                return self.round(cr, uid, to_currency, from_amount)
            else:
                return from_amount
        else:
            if round:
                return self.round(cr, uid, to_currency, from_amount * rate)
            else:
                return (from_amount * rate)

    def name_search(self, cr, uid, name, args=[], operator='ilike', context={}, limit=80):
        args2 = args[:]
        if name:
            args += [('name', operator, name)]
            args2 += [('code', operator, name)]
        ids = self.search(cr, uid, args, limit=limit)
        ids += self.search(cr, uid, args2, limit=limit)
        res = self.name_get(cr, uid, ids, context)
        return res
res_currency()

class res_currency_rate(osv.osv):
    _name = "res.currency.rate"
    _description = "Currency Rate"
    _columns = {
        'name': fields.date('Date', required=True, select=True),
        'rate': fields.float('Rate', digits=(12,6), required=True,
            help='The rate of the currency to the currency of rate 1'),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d'),
    }
    _order = "name desc"
res_currency_rate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

