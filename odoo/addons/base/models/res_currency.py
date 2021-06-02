# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math
import re
import time
import traceback

from odoo import api, fields, models, tools, _
from odoo.tools.misc import get_lang

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None

CURRENCY_DISPLAY_PATTERN = re.compile(r'(\w+)\s*(?:\((.*)\))?')


class Currency(models.Model):
    _name = "res.currency"
    _description = "Currency"
    _order = 'active desc, name'

    # Note: 'code' column was removed as of v6.0, the 'name' should now hold the ISO code.
    name = fields.Char(string='Currency', size=3, required=True, help="Currency Code (ISO 4217)")
    symbol = fields.Char(help="Currency sign, to be used when printing amounts.", required=True)
    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits=0,
                        help='The rate of the currency to the currency of rate 1.')
    rate_ids = fields.One2many('res.currency.rate', 'currency_id', string='Rates')
    rounding = fields.Float(string='Rounding Factor', digits=(12, 6), default=0.01)
    decimal_places = fields.Integer(compute='_compute_decimal_places', store=True)
    active = fields.Boolean(default=True)
    position = fields.Selection([('after', 'After Amount'), ('before', 'Before Amount')], default='after',
        string='Symbol Position', help="Determines where the currency symbol should be placed after or before the amount.")
    date = fields.Date(compute='_compute_date')
    currency_unit_label = fields.Char(string="Currency Unit", help="Currency Unit Name")
    currency_subunit_label = fields.Char(string="Currency Subunit", help="Currency Subunit Name")

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'The currency code must be unique!'),
        ('rounding_gt_zero', 'CHECK (rounding>0)', 'The rounding factor must be greater than 0!')
    ]

    def _get_rates(self, company, date):
        self.env['res.currency.rate'].flush(['rate', 'currency_id', 'company_id', 'name'])
        query = """SELECT c.id,
                          COALESCE((SELECT r.rate FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    @api.depends('rate_ids.rate')
    def _compute_current_rate(self):
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = self._get_rates(company, date)
        for currency in self:
            currency.rate = currency_rates.get(currency.id) or 1.0

    @api.depends('rounding')
    def _compute_decimal_places(self):
        for currency in self:
            if 0 < currency.rounding < 1:
                currency.decimal_places = int(math.ceil(math.log10(1/currency.rounding)))
            else:
                currency.decimal_places = 0

    @api.depends('rate_ids.name')
    def _compute_date(self):
        for currency in self:
            currency.date = currency.rate_ids[:1].name

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        results = super(Currency, self)._name_search(name, args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        if not results:
            name_match = CURRENCY_DISPLAY_PATTERN.match(name)
            if name_match:
                results = super(Currency, self)._name_search(name_match.group(1), args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        return results

    def name_get(self):
        return [(currency.id, tools.ustr(currency.name)) for currency in self]

    def amount_to_text(self, amount):
        self.ensure_one()
        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()

        if num2words is None:
            logging.getLogger(__name__).warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(self.decimal_places) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        lang_code = self.env.context.get('lang') or self.env.user.lang or get_lang(self.env).code
        lang = self.env['res.lang'].with_context(active_test=False).search([('code', '=', lang_code)])
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
                        amt_value=_num2words(integer_value, lang=lang.iso_code),
                        amt_word=self.currency_unit_label,
                        )
        if not self.is_zero(amount - integer_value):
            amount_words += ' ' + _('and') + tools.ustr(' {amt_value} {amt_word}').format(
                        amt_value=_num2words(fractional_value, lang=lang.iso_code),
                        amt_word=self.currency_subunit_label,
                        )
        return amount_words

    def round(self, amount):
        """Return ``amount`` rounded  according to ``self``'s rounding rules.

           :param float amount: the amount to round
           :return: rounded float
        """
        self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.rounding)

    def compare_amounts(self, amount1, amount2):
        """Compare ``amount1`` and ``amount2`` after rounding them according to the
           given currency's precision..
           An amount is considered lower/greater than another amount if their rounded
           value is different. This is not the same as having a non-zero difference!

           For example 1.432 and 1.431 are equal at 2 digits precision,
           so this method would return 0.
           However 0.006 and 0.002 are considered different (returns 1) because
           they respectively round to 0.01 and 0.0, even though
           0.006-0.002 = 0.004 which would be considered zero at 2 digits precision.

           :param float amount1: first amount to compare
           :param float amount2: second amount to compare
           :return: (resp.) -1, 0 or 1, if ``amount1`` is (resp.) lower than,
                    equal to, or greater than ``amount2``, according to
                    ``currency``'s rounding.

           With the new API, call it like: ``currency.compare_amounts(amount1, amount2)``.
        """
        self.ensure_one()
        return tools.float_compare(amount1, amount2, precision_rounding=self.rounding)

    def is_zero(self, amount):
        """Returns true if ``amount`` is small enough to be treated as
           zero according to current currency's rounding rules.
           Warning: ``is_zero(amount1-amount2)`` is not always equivalent to
           ``compare_amounts(amount1,amount2) == 0``, as the former will round after
           computing the difference, while the latter will round before, giving
           different results for e.g. 0.006 and 0.002 at 2 digits precision.

           :param float amount: amount to compare with currency's zero

           With the new API, call it like: ``currency.is_zero(amount)``.
        """
        self.ensure_one()
        return tools.float_is_zero(amount, precision_rounding=self.rounding)

    @api.model
    def _get_conversion_rate(self, from_currency, to_currency, company, date):
        currency_rates = (from_currency + to_currency)._get_rates(company, date)
        res = currency_rates.get(to_currency.id) / currency_rates.get(from_currency.id)
        return res

    def _convert(self, from_amount, to_currency, company, date, round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self
        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount

    @api.model
    def _compute(self, from_currency, to_currency, from_amount, round=True):
        _logger.warning('The `_compute` method is deprecated. Use `_convert` instead')
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        return from_currency._convert(from_amount, to_currency, company, date)

    def compute(self, from_amount, to_currency, round=True):
        _logger.warning('The `compute` method is deprecated. Use `_convert` instead')
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        return self._convert(from_amount, to_currency, company, date)

    def _select_companies_rates(self):
        return """
            SELECT
                r.currency_id,
                COALESCE(r.company_id, c.id) as company_id,
                r.rate,
                r.name AS date_start,
                (SELECT name FROM res_currency_rate r2
                 WHERE r2.name > r.name AND
                       r2.currency_id = r.currency_id AND
                       (r2.company_id is null or r2.company_id = c.id)
                 ORDER BY r2.name ASC
                 LIMIT 1) AS date_end
            FROM res_currency_rate r
            JOIN res_company c ON (r.company_id is null or r.company_id = c.id)
        """


class CurrencyRate(models.Model):
    _name = "res.currency.rate"
    _description = "Currency Rate"
    _order = "name desc"

    name = fields.Date(string='Date', required=True, index=True,
                           default=lambda self: fields.Date.today())
    rate = fields.Float(digits=0, default=1.0, help='The rate of the currency to the currency of rate 1')
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    _sql_constraints = [
        ('unique_name_per_day', 'unique (name,currency_id,company_id)', 'Only one currency rate per day allowed!'),
        ('currency_rate_check', 'CHECK (rate>0)', 'The currency rate must be strictly positive.'),
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if operator in ['=', '!=']:
            try:
                date_format = '%Y-%m-%d'
                if self._context.get('lang'):
                    lang_id = self.env['res.lang']._search([('code', '=', self._context['lang'])], access_rights_uid=name_get_uid)
                    if lang_id:
                        date_format = self.browse(lang_id).date_format
                name = time.strftime('%Y-%m-%d', time.strptime(name, date_format))
            except ValueError:
                try:
                    args.append(('rate', operator, float(name)))
                except ValueError:
                    return []
                name = ''
                operator = 'ilike'
        return super(CurrencyRate, self)._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
