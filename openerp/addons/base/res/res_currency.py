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
import re
import time
import netsvc
from osv import fields, osv
import tools

from tools.misc import currency
from tools.translate import _

CURRENCY_DISPLAY_PATTERN = re.compile(r'(\w+)\s*(?:\((.*)\))?')

class res_currency(osv.osv):
    def _current_rate(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        if 'date' in context:
            date = context['date']
        else:
            date = time.strftime('%Y-%m-%d')
        date = date or time.strftime('%Y-%m-%d')
        # Convert False values to None ...
        currency_rate_type = context.get('currency_rate_type_id') or None
        # ... and use 'is NULL' instead of '= some-id'.
        operator = '=' if currency_rate_type else 'is'
        for id in ids:
            cr.execute("SELECT currency_id, rate FROM res_currency_rate WHERE currency_id = %s AND name <= %s AND currency_rate_type_id " + operator +" %s ORDER BY name desc LIMIT 1" ,(id, date, currency_rate_type))
            if cr.rowcount:
                id, rate = cr.fetchall()[0]
                res[id] = rate
            else:
                res[id] = 0
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
        'base': fields.boolean('Base'),
        'position': fields.selection([('after','After Amount'),('before','Before Amount')], 'Symbol position', help="Determines where the currency symbol should be placed after or before the amount.")
    }
    _defaults = {
        'active': lambda *a: 1,
        'position' : 'after',
        'rounding': 0.01,
        'accuracy': 4,
    }
    _sql_constraints = [
        # this constraint does not cover all cases due to SQL NULL handling for company_id,
        # so it is complemented with a unique index (see below). The constraint and index
        # share the same prefix so that IntegrityError triggered by the index will be caught
        # and reported to the user with the constraint's error message.
        ('unique_name_company_id', 'unique (name, company_id)', 'The currency code must be unique per company!'),
    ]
    _order = "name"

    def init(self, cr):
        # CONSTRAINT/UNIQUE INDEX on (name,company_id) 
        # /!\ The unique constraint 'unique_name_company_id' is not sufficient, because SQL92
        # only support field names in constraint definitions, and we need a function here:
        # we need to special-case company_id to treat all NULL company_id as equal, otherwise
        # we would allow duplicate "global" currencies (all having company_id == NULL) 
        cr.execute("""SELECT indexname FROM pg_indexes WHERE indexname = 'res_currency_unique_name_company_id_idx'""")
        if not cr.fetchone():
            cr.execute("""CREATE UNIQUE INDEX res_currency_unique_name_company_id_idx
                          ON res_currency
                          (name, (COALESCE(company_id,-1)))""")

    def read(self, cr, user, ids, fields=None, context=None, load='_classic_read'):
        res = super(res_currency, self).read(cr, user, ids, fields, context, load)
        currency_rate_obj = self.pool.get('res.currency.rate')
        for r in res:
            if r.__contains__('rate_ids'):
                rates=r['rate_ids']
                if rates:
                    currency_date = currency_rate_obj.read(cr, user, rates[0], ['name'])['name']
                    r['date'] = currency_date
        return res

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        if name:
            ids = self.search(cr, user, ([('name','=',name)] + args), limit=limit, context=context)
            name_match = CURRENCY_DISPLAY_PATTERN.match(name)
            if not ids and name_match:
               ids = self.search(cr, user, [('name','=', name_match.group(1))] + args, limit=limit, context=context)
        else:
            ids = self.search(cr, user, args, limit=limit, context=context)
        return self.name_get(cr, user, ids, context=context)

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
        ctx = context.copy()
        ctx.update({'currency_rate_type_id': ctx.get('currency_rate_type_from')})
        from_currency = self.browse(cr, uid, from_currency.id, context=ctx)

        ctx.update({'currency_rate_type_id': ctx.get('currency_rate_type_to')})
        to_currency = self.browse(cr, uid, to_currency.id, context=ctx)

        if from_currency.rate == 0 or to_currency.rate == 0:
            date = context.get('date', time.strftime('%Y-%m-%d'))
            if from_currency.rate == 0:
                currency_symbol = from_currency.symbol
            else:
                currency_symbol = to_currency.symbol
            raise osv.except_osv(_('Error'), _('No rate found \n' \
                    'for the currency: %s \n' \
                    'at the date: %s') % (currency_symbol, date))
        return to_currency.rate/from_currency.rate

    def compute(self, cr, uid, from_currency_id, to_currency_id, from_amount,
                round=True, currency_rate_type_from=False, currency_rate_type_to=False, context=None):
        if not context:
            context = {}
        if not from_currency_id:
            from_currency_id = to_currency_id
        if not to_currency_id:
            to_currency_id = from_currency_id
        xc = self.browse(cr, uid, [from_currency_id,to_currency_id], context=context)
        from_currency = (xc[0].id == from_currency_id and xc[0]) or xc[1]
        to_currency = (xc[0].id == to_currency_id and xc[0]) or xc[1]
        if (to_currency_id == from_currency_id) and (currency_rate_type_from == currency_rate_type_to):
            if round:
                return self.round(cr, uid, to_currency, from_amount)
            else:
                return from_amount
        else:
            context.update({'currency_rate_type_from': currency_rate_type_from, 'currency_rate_type_to': currency_rate_type_to})
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
        'name': fields.char('Name', size=64, required=True, translate=True),
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
        'currency_rate_type_id': fields.many2one('res.currency.rate.type', 'Currency Rate Type', help="Allow you to define your own currency rate types, like 'Average' or 'Year to Date'. Leave empty if you simply want to use the normal 'spot' rate type"),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d'),
    }
    _order = "name desc"

res_currency_rate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

