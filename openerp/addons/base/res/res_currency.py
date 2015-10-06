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
import math

from openerp import api, fields as fields2
from openerp import tools
from openerp.osv import fields, osv
from openerp.tools import float_round, float_is_zero, float_compare
from openerp.tools.translate import _
import simplejson as json

CURRENCY_DISPLAY_PATTERN = re.compile(r'(\w+)\s*(?:\((.*)\))?')

class res_currency(osv.osv):
    def _current_rate(self, cr, uid, ids, name, arg, context=None):
        return self._get_current_rate(cr, uid, ids, context=context)

    def _current_rate_silent(self, cr, uid, ids, name, arg, context=None):
        return self._get_current_rate(cr, uid, ids, raise_on_no_rate=False, context=context)

    def _get_current_rate(self, cr, uid, ids, raise_on_no_rate=True, context=None):
        if context is None:
            context = {}
        res = {}

        date = context.get('date') or time.strftime('%Y-%m-%d')
        for id in ids:
            cr.execute('SELECT rate FROM res_currency_rate '
                       'WHERE currency_id = %s '
                         'AND name <= %s '
                       'ORDER BY name desc LIMIT 1',
                       (id, date))
            if cr.rowcount:
                res[id] = cr.fetchone()[0]
            elif not raise_on_no_rate:
                res[id] = 0
            else:
                currency = self.browse(cr, uid, id, context=context)
                raise osv.except_osv(_('Error!'),_("No currency rate associated for currency '%s' for the given period" % (currency.name)))
        return res

    _name = "res.currency"
    _description = "Currency"
    _columns = {
        # Note: 'code' column was removed as of v6.0, the 'name' should now hold the ISO code.
        'name': fields.char('Currency', size=3, required=True, help="Currency Code (ISO 4217)"),
        'symbol': fields.char('Symbol', size=4, help="Currency sign, to be used when printing amounts."),
        'rate': fields.function(_current_rate, string='Current Rate', digits=(12,6),
            help='The rate of the currency to the currency of rate 1.'),

        # Do not use for computation ! Same as rate field with silent failing
        'rate_silent': fields.function(_current_rate_silent, string='Current Rate', digits=(12,6),
            help='The rate of the currency to the currency of rate 1 (0 if no rate defined).'),
        'rate_ids': fields.one2many('res.currency.rate', 'currency_id', 'Rates'),
        'accuracy': fields.integer('Computational Accuracy'),
        'rounding': fields.float('Rounding Factor', digits=(12,6)),
        'active': fields.boolean('Active'),
        'company_id':fields.many2one('res.company', 'Company'),
        'base': fields.boolean('Base'),
        'position': fields.selection([('after','After Amount'),('before','Before Amount')], 'Symbol Position', help="Determines where the currency symbol should be placed after or before the amount.")
    }
    _defaults = {
        'active': 1,
        'position' : 'after',
        'rounding': 0.01,
        'accuracy': 4,
        'company_id': False,
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

    date = fields2.Date(compute='compute_date')

    @api.one
    @api.depends('rate_ids.name')
    def compute_date(self):
        self.date = self.rate_ids[:1].name

    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        results = super(res_currency,self)\
            .name_search(cr, user, name, args, operator=operator, context=context, limit=limit)
        if not results:
            name_match = CURRENCY_DISPLAY_PATTERN.match(name)
            if name_match:
                results = super(res_currency,self)\
                    .name_search(cr, user, name_match.group(1), args, operator=operator, context=context, limit=limit)
        return results

    def name_get(self, cr, uid, ids, context=None):
        if not ids:
            return []
        if isinstance(ids, (int, long)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name','symbol'], context=context, load='_classic_write')
        return [(x['id'], tools.ustr(x['name'])) for x in reads]

    def copy(self, cr, uid, id, default=None, context=None):
        if context is None:
            context = {}
        if not default:
            default = {}
        default.update(name=_("%s (copy)")
                       % (self.browse(cr, uid, id, context=context).name))
        return super(res_currency, self).copy(
            cr, uid, id, default=default, context=context)

    @api.v8
    def round(self, amount):
        """ Return `amount` rounded according to currency `self`. """
        return float_round(amount, precision_rounding=self.rounding)

    @api.v7
    def round(self, cr, uid, currency, amount):
        """Return ``amount`` rounded  according to ``currency``'s
           rounding rules.

           :param Record currency: currency for which we are rounding
           :param float amount: the amount to round
           :return: rounded float
        """
        return float_round(amount, precision_rounding=currency.rounding)

    @api.v8
    def compare_amounts(self, amount1, amount2):
        """ Compare `amount1` and `amount2` after rounding them according to
            `self`'s precision. An amount is considered lower/greater than
            another amount if their rounded value is different. This is not the
            same as having a non-zero difference!

            For example 1.432 and 1.431 are equal at 2 digits precision, so this
            method would return 0. However 0.006 and 0.002 are considered
            different (returns 1) because they respectively round to 0.01 and
            0.0, even though 0.006-0.002 = 0.004 which would be considered zero
            at 2 digits precision.
        """
        return float_compare(amount1, amount2, precision_rounding=self.rounding)

    @api.v7
    def compare_amounts(self, cr, uid, currency, amount1, amount2):
        """Compare ``amount1`` and ``amount2`` after rounding them according to the
           given currency's precision..
           An amount is considered lower/greater than another amount if their rounded
           value is different. This is not the same as having a non-zero difference!

           For example 1.432 and 1.431 are equal at 2 digits precision,
           so this method would return 0.
           However 0.006 and 0.002 are considered different (returns 1) because
           they respectively round to 0.01 and 0.0, even though
           0.006-0.002 = 0.004 which would be considered zero at 2 digits precision.

           :param Record currency: currency for which we are rounding
           :param float amount1: first amount to compare
           :param float amount2: second amount to compare
           :return: (resp.) -1, 0 or 1, if ``amount1`` is (resp.) lower than,
                    equal to, or greater than ``amount2``, according to
                    ``currency``'s rounding.
        """
        return float_compare(amount1, amount2, precision_rounding=currency.rounding)

    @api.v8
    def is_zero(self, amount):
        """ Return true if `amount` is small enough to be treated as zero
            according to currency `self`'s rounding rules.

            Warning: ``is_zero(amount1-amount2)`` is not always equivalent to 
            ``compare_amounts(amount1,amount2) == 0``, as the former will round
            after computing the difference, while the latter will round before,
            giving different results, e.g., 0.006 and 0.002 at 2 digits precision.
        """
        return float_is_zero(amount, precision_rounding=self.rounding)

    @api.v7
    def is_zero(self, cr, uid, currency, amount):
        """Returns true if ``amount`` is small enough to be treated as
           zero according to ``currency``'s rounding rules.

           Warning: ``is_zero(amount1-amount2)`` is not always equivalent to 
           ``compare_amounts(amount1,amount2) == 0``, as the former will round after
           computing the difference, while the latter will round before, giving
           different results for e.g. 0.006 and 0.002 at 2 digits precision.

           :param Record currency: currency for which we are rounding
           :param float amount: amount to compare with currency's zero
        """
        return float_is_zero(amount, precision_rounding=currency.rounding)

    def _get_conversion_rate(self, cr, uid, from_currency, to_currency, context=None):
        if context is None:
            context = {}
        ctx = context.copy()
        from_currency = self.browse(cr, uid, from_currency.id, context=ctx)
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

    def _compute(self, cr, uid, from_currency, to_currency, from_amount, round=True, context=None):
        if (to_currency.id == from_currency.id):
            if round:
                return self.round(cr, uid, to_currency, from_amount)
            else:
                return from_amount
        else:
            rate = self._get_conversion_rate(cr, uid, from_currency, to_currency, context=context)
            if round:
                return self.round(cr, uid, to_currency, from_amount * rate)
            else:
                return from_amount * rate

    @api.v7
    def compute(self, cr, uid, from_currency_id, to_currency_id, from_amount,
                round=True, context=None):
        context = context or {}
        if not from_currency_id:
            from_currency_id = to_currency_id
        if not to_currency_id:
            to_currency_id = from_currency_id
        xc = self.browse(cr, uid, [from_currency_id,to_currency_id], context=context)
        from_currency = (xc[0].id == from_currency_id and xc[0]) or xc[1]
        to_currency = (xc[0].id == to_currency_id and xc[0]) or xc[1]
        return self._compute(cr, uid, from_currency, to_currency, from_amount, round, context)

    @api.v8
    def compute(self, from_amount, to_currency, round=True):
        """ Convert `from_amount` from currency `self` to `to_currency`. """
        assert self, "compute from unknown currency"
        assert to_currency, "compute to unknown currency"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            to_amount = from_amount * self._get_conversion_rate(self, to_currency)
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount

    def get_format_currencies_js_function(self, cr, uid, context=None):
        """ Returns a string that can be used to instanciate a javascript function that formats numbers as currencies.
            That function expects the number as first parameter and the currency id as second parameter. In case of failure it returns undefined."""
        function = ""
        for row in self.search_read(cr, uid, domain=[], fields=['id', 'name', 'symbol', 'rounding', 'position'], context=context):
            digits = int(math.ceil(math.log10(1 / row['rounding'])))
            symbol = row['symbol'] or row['name']

            format_number_str = "openerp.web.format_value(arguments[0], {type: 'float', digits: [69," + str(digits) + "]}, 0.00)"
            if row['position'] == 'after':
                return_str = "return " + format_number_str + " + '\\xA0' + " + json.dumps(symbol) + ";"
            else:
                return_str = "return " + json.dumps(symbol) + " + '\\xA0' + " + format_number_str + ";"
            function += "if (arguments[1] === " + str(row['id']) + ") { " + return_str + " }"
        return function

class res_currency_rate(osv.osv):
    _name = "res.currency.rate"
    _description = "Currency Rate"

    _columns = {
        'name': fields.datetime('Date', required=True, select=True),
        'rate': fields.float('Rate', digits=(12, 6), help='The rate of the currency to the currency of rate 1'),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d 00:00:00'),
    }
    _order = "name desc"

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=80):
        if operator in ['=', '!=']:
            try:
                date_format = '%Y-%m-%d'
                if context.get('lang'):
                    lang_obj = self.pool['res.lang']
                    lang_ids = lang_obj.search(cr, user, [('code', '=', context['lang'])], context=context)
                    if lang_ids:
                        date_format = lang_obj.browse(cr, user, lang_ids[0], context=context).date_format
                name = time.strftime('%Y-%m-%d', time.strptime(name, date_format))
            except ValueError:
                try:
                    args.append(('rate', operator, float(name)))
                except ValueError:
                    return []
                name = ''
                operator = 'ilike'
        return super(res_currency_rate, self).name_search(cr, user, name, args=args, operator=operator, context=context, limit=limit)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
