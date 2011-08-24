# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import netsvc
from osv import fields, osv
import tools

from tools.misc import currency
from tools.translate import _

class res_currency(osv.osv):
    def _current_rate(self, cr, uid, ids, name, arg, context=None):
        currency_rate_obj = self.pool.get('res.currency.rate')
        res = {}
        if context is None:
            context = {}
        if 'date' in context:
            date = context['date']
        else:
            date = time.strftime('%Y-%m-%d')
        domain = [('currency_id', 'in', ids), ('name', '<=', date)]
        currency_rate_type_id = context.get('currency_rate_type_id', False)
        if currency_rate_type_id:
            domain.append(('currency_rate_type_id', '=', currency_rate_type_id))
        curr_rate_ids = currency_rate_obj.search(cr, uid, domain, order='name desc', context=context)
        curr_rates = currency_rate_obj.browse(cr, uid, curr_rate_ids, context=context)
        for id in ids:
            res[id] = 0
            for cur in curr_rates:
                if cur.currency_id.id == id:
                    res[id] = cur.rate
                    break
        return res

    _name = "res.currency"
    _description = "Currency"
    _columns = {
        # Note: 'code' column was removed as of v6.0, the 'name' should now hold the ISO code.
        'name': fields.char('Currency', size=32, required=True, help="Currency Code (ISO 4217)"),
        'symbol': fields.char('Symbol', size=3, help="Currency sign, to be used when printing amounts."),
        'rate': fields.function(_current_rate, method=True, string='Current Rate', digits=(12,6),
            help='The rate of the currency to the currency of rate 1.'),
        'rate_ids': fields.one2many('res.currency.rate', 'currency_id', 'Rates'),
        'accuracy': fields.integer('Computational Accuracy'),
        'rounding': fields.float('Rounding Factor', digits=(12,6)),
        'active': fields.boolean('Active'),
        'company_id':fields.many2one('res.company', 'Company'),
        'date': fields.date('Date'),
        'base': fields.boolean('Base')

    }
    _defaults = {
        'active': lambda *a: 1,
        'company_id': lambda self,cr,uid,c: self.pool.get('res.company')._company_default_get(cr, uid, 'res.currency', context=c)
    }
    _order = "name"

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        currency_rate_obj=  self.pool.get('res.currency.rate')
        res = super(osv.osv, self).read(cr, user, ids, fields, context, load)
        for r in res:
            if r.__contains__('rate_ids'):
                rates=r['rate_ids']
                if rates:
                    currency_date = currency_rate_obj.read(cr, user, rates[0], ['name'])['name']
                    r['date'] = currency_date
        return res

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','symbol'], context=context, load='_classic_write')
        return [(x['id'], tools.ustr(x['name']) + (x['symbol'] and (' (' + tools.ustr(x['symbol']) + ')') or '')) for x in reads]

    def round(self, cr, uid, currency, amount):
        if currency.rounding == 0:
            return 0.0
        else:
            # /!\ First member below must be rounded to full unit!
            # Do not pass a rounding digits value to round()
            return round(amount / currency.rounding) * currency.rounding

    def is_zero(self, cr, uid, currency, amount):
        return abs(self.round(cr, uid, currency, amount)) < currency.rounding

    def _get_conversion_rate(self, cr, uid, from_currency, to_currency, context=None):
        if context is None:
            context = {}
        if from_currency['rate'] == 0 or to_currency['rate'] == 0:
            date = context.get('date', time.strftime('%Y-%m-%d'))
            if from_currency['rate'] == 0:
                currency_symbol = from_currency.symbol
            else:
                currency_symbol = to_currency.symbol
            raise osv.except_osv(_('Error'), _('No rate found \n' \
                    'for the currency: %s \n' \
                    'at the date: %s') % (currency_symbol, date))

        return to_currency.rate/from_currency.rate

    def compute(self, cr, uid, from_currency_id, to_currency_id, from_amount,
                round=True, currency_rate_type_from=False, currency_rate_type_to=False, context=None):
        if not from_currency_id:
            from_currency_id = to_currency_id
        if not to_currency_id:
            to_currency_id = from_currency_id

        context.update({'currency_rate_type_id': currency_rate_type_from})
        xc = self.browse(cr, uid, [from_currency_id], context=context)
        context.update({'currency_rate_type_id': currency_rate_type_to})
        xc1 = self.browse(cr, uid, [to_currency_id], context=context)
        from_currency = (xc[0].id == from_currency_id and xc[0]) or xc[1]
        to_currency = (xc1[0].id == to_currency_id and xc1[0]) or xc1[1]
        if to_currency_id == from_currency_id:
            if round:
                return self.round(cr, uid, to_currency, from_amount)
            else:
                return from_amount
        else:
            rate = self._get_conversion_rate(cr, uid, from_currency, to_currency, context=context)
            if round:
                return self.round(cr, uid, to_currency, from_amount * rate)
            else:
                return (from_amount * rate)

res_currency()

class res_currency_rate_type(osv.osv):
    _name = "res.currency.rate.type"
    _description = "Currency Rate Type"
    _columns = {
        'name': fields.char('Name', size=32, required=True),
    }

res_currency_rate_type()

class res_currency_rate(osv.osv):
    _name = "res.currency.rate"
    _description = "Currency Rate"
    _columns = {
        'name': fields.date('Date', required=True, select=True),
        'rate': fields.float('Rate', digits=(12,6), required=True,
            help='The rate of the currency to the currency of rate 1'),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'currency_rate_type_id': fields.many2one('res.currency.rate.type', 'Currency Rate Type'),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d'),
    }
    _order = "name desc"

res_currency_rate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

