# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import math

from lxml import etree

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import parse_date

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class Currency(models.Model):
    _name = "res.currency"
    _description = "Currency"
    _rec_names_search = ['name', 'full_name']
    _order = 'active desc, name'

    # Note: 'code' column was removed as of v6.0, the 'name' should now hold the ISO code.
    name = fields.Char(string='Currency', size=3, required=True, help="Currency Code (ISO 4217)")
    full_name = fields.Char(string='Name')
    symbol = fields.Char(help="Currency sign, to be used when printing amounts.", required=True)
    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits=0,
                        help='The rate of the currency to the currency of rate 1.')
    inverse_rate = fields.Float(compute='_compute_current_rate', digits=0, readonly=True,
                                help='The currency of rate 1 to the rate of the currency.')
    rate_string = fields.Char(compute='_compute_current_rate')
    rate_ids = fields.One2many('res.currency.rate', 'currency_id', string='Rates')
    rounding = fields.Float(string='Rounding Factor', digits=(12, 6), default=0.01,
        help='Amounts in this currency are rounded off to the nearest multiple of the rounding factor.')
    decimal_places = fields.Integer(compute='_compute_decimal_places', store=True,
        help='Decimal places taken into account for operations on amounts in this currency. It is determined by the rounding factor.')
    active = fields.Boolean(default=True)
    position = fields.Selection([('after', 'After Amount'), ('before', 'Before Amount')], default='after',
        string='Symbol Position', help="Determines where the currency symbol should be placed after or before the amount.")
    date = fields.Date(compute='_compute_date')
    currency_unit_label = fields.Char(string="Currency Unit")
    currency_subunit_label = fields.Char(string="Currency Subunit")
    is_current_company_currency = fields.Boolean(compute='_compute_is_current_company_currency')

    _sql_constraints = [
        ('unique_name', 'unique (name)', 'The currency code must be unique!'),
        ('rounding_gt_zero', 'CHECK (rounding>0)', 'The rounding factor must be greater than 0!')
    ]

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._toggle_group_multi_currency()
        # Currency info is cached to reduce the number of SQL queries when building the session
        # info. See `ir_http.get_currencies`.
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self._toggle_group_multi_currency()
        # Currency info is cached to reduce the number of SQL queries when building the session
        # info. See `ir_http.get_currencies`.
        self.env.registry.clear_cache()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'active' not in vals:
            return res
        if set(vals.keys()) & {'active', 'digits', 'position', 'symbol'}:
            # Currency info is cached to reduce the number of SQL queries when building the session
            # info. See `ir_http.get_currencies`.
            self.env.registry.clear_cache()
        self._toggle_group_multi_currency()
        return res

    @api.model
    def _toggle_group_multi_currency(self):
        """
        Automatically activate group_multi_currency if there is more than 1 active currency; deactivate it otherwise
        """
        active_currency_count = self.search_count([('active', '=', True)])
        if active_currency_count > 1:
            self._activate_group_multi_currency()
        elif active_currency_count <= 1:
            self._deactivate_group_multi_currency()

    @api.model
    def _activate_group_multi_currency(self):
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        group_mc = self.env.ref('base.group_multi_currency', raise_if_not_found=False)
        if group_user and group_mc:
            group_user.sudo()._apply_group(group_mc)

    @api.model
    def _deactivate_group_multi_currency(self):
        group_user = self.env.ref('base.group_user', raise_if_not_found=False)
        group_mc = self.env.ref('base.group_multi_currency', raise_if_not_found=False)
        if group_user and group_mc:
            group_user.sudo()._remove_group(group_mc.sudo())

    @api.constrains('active')
    def _check_company_currency_stays_active(self):
        if self._context.get('install_mode') or self._context.get('force_deactivate'):
            # install_mode : At install, when this check is run, the "active" field of a currency added to a company will
            #                still be evaluated as False, despite it's automatically set at True when added to the company.
            # force_deactivate : Allows deactivation of a currency in tests to enable non multi_currency behaviors
            return

        currencies = self.filtered(lambda c: not c.active)
        if self.env['res.company'].search([('currency_id', 'in', currencies.ids)]):
            raise UserError(_("This currency is set on a company and therefore cannot be deactivated."))

    def _get_rates(self, company, date):
        if not self.ids:
            return {}
        self.env['res.currency.rate'].flush_model(['rate', 'currency_id', 'company_id', 'name'])
        query = """SELECT c.id,
                          COALESCE((SELECT r.rate FROM res_currency_rate r
                                  WHERE r.currency_id = c.id AND r.name <= %s
                                    AND (r.company_id IS NULL OR r.company_id = %s)
                               ORDER BY r.company_id, r.name DESC
                                  LIMIT 1), 1.0) AS rate
                   FROM res_currency c
                   WHERE c.id IN %s"""
        self._cr.execute(query, (date, company.root_id.id, tuple(self.ids)))
        currency_rates = dict(self._cr.fetchall())
        return currency_rates

    @api.depends_context('company')
    def _compute_is_current_company_currency(self):
        for currency in self:
            currency.is_current_company_currency = self.env.company.root_id.currency_id == currency

    @api.depends('rate_ids.rate')
    @api.depends_context('to_currency', 'date', 'company', 'company_id')
    def _compute_current_rate(self):
        date = self._context.get('date') or fields.Date.context_today(self)
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        company = company.root_id
        to_currency = self.browse(self.env.context.get('to_currency')) or company.currency_id
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = (self + to_currency)._get_rates(self.env.company, date)
        for currency in self:
            currency.rate = currency_rates.get(to_currency.id) / currency_rates.get(currency.id)
            currency.inverse_rate = 1 / currency.rate
            if currency != company.currency_id:
                currency.rate_string = '1 %s = %.6f %s' % (to_currency.name, currency.rate, currency.name)
            else:
                currency.rate_string = ''

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

        lang = tools.get_lang(self.env)
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

    def format(self, amount):
        """Return ``amount`` formatted according to ``self``'s rounding rules, symbols and positions.

           Also take care of removing the minus sign when 0.0 is negative

           :param float amount: the amount to round
           :return: formatted str
        """
        self.ensure_one()
        return tools.format_amount(self.env, amount + 0.0, self)

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
    def _get_conversion_rate(self, from_currency, to_currency, company=None, date=None):
        if from_currency == to_currency:
            return 1
        company = company or self.env.company
        date = date or fields.Date.context_today(self)
        return from_currency.with_company(company).with_context(to_currency=to_currency.id, date=str(date)).rate

    def _convert(self, from_amount, to_currency, company=None, date=None, round=True):  # noqa: A002 builtin-argument-shadowing
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
        # apply conversion rate
        if from_amount:
            to_amount = from_amount * self._get_conversion_rate(self, to_currency, company, date)
        else:
            return 0.0

        # apply rounding
        return to_currency.round(to_amount) if round else to_amount

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

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the rate field labels according to the company currency
        makes the view cache dependent on the company currency"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + ((self.env['res.company'].browse(self._context.get('company_id')) or self.env.company.root_id).currency_id.name,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('tree', 'form'):
            currency_name = (self.env['res.company'].browse(self._context.get('company_id')) or self.env.company.root_id).currency_id.name
            for field in [['company_rate', _('Unit per %s', currency_name)],
                          ['inverse_company_rate', _('%s per Unit', currency_name)]]:
                node = arch.xpath("//tree//field[@name='%s']" % field[0])
                if node:
                    node[0].set('string', field[1])
        return arch, view


class CurrencyRate(models.Model):
    _name = "res.currency.rate"
    _description = "Currency Rate"
    _rec_names_search = ['name', 'rate']
    _order = "name desc"

    name = fields.Date(string='Date', required=True, index=True,
                           default=fields.Date.context_today)
    rate = fields.Float(
        digits=0,
        group_operator="avg",
        help='The rate of the currency to the currency of rate 1',
        string='Technical Rate'
    )
    company_rate = fields.Float(
        digits=0,
        compute="_compute_company_rate",
        inverse="_inverse_company_rate",
        group_operator="avg",
        help="The currency of rate 1 to the rate of the currency.",
    )
    inverse_company_rate = fields.Float(
        digits=0,
        compute="_compute_inverse_company_rate",
        inverse="_inverse_inverse_company_rate",
        group_operator="avg",
        help="The rate of the currency to the currency of rate 1 ",
    )
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, required=True, ondelete="cascade")
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.root_id)

    _sql_constraints = [
        ('unique_name_per_day', 'unique (name,currency_id,company_id)', 'Only one currency rate per day allowed!'),
        ('currency_rate_check', 'CHECK (rate>0)', 'The currency rate must be strictly positive.'),
    ]

    def _sanitize_vals(self, vals):
        if 'inverse_company_rate' in vals and ('company_rate' in vals or 'rate' in vals):
            del vals['inverse_company_rate']
        if 'company_rate' in vals and 'rate' in vals:
            del vals['company_rate']
        return vals

    def write(self, vals):
        self.env['res.currency'].invalidate_model(['rate'])
        return super().write(self._sanitize_vals(vals))

    @api.model_create_multi
    def create(self, vals_list):
        self.env['res.currency'].invalidate_model(['rate'])
        return super().create([self._sanitize_vals(vals) for vals in vals_list])

    def _get_latest_rate(self):
        # Make sure 'name' is defined when creating a new rate.
        if not self.name:
            raise UserError(_("The name for the current rate is empty.\nPlease set it."))
        return self.currency_id.rate_ids.sudo().filtered(lambda x: (
            x.rate
            and x.company_id == (self.company_id or self.env.company.root_id)
            and x.name < (self.name or fields.Date.today())
        )).sorted('name')[-1:]

    def _get_last_rates_for_companies(self, companies):
        return {
            company: company.currency_id.rate_ids.sudo().filtered(lambda x: (
                x.rate
                and x.company_id == company or not x.company_id
            )).sorted('name')[-1:].rate or 1
            for company in companies
        }

    @api.depends('currency_id', 'company_id', 'name')
    def _compute_rate(self):
        for currency_rate in self:
            currency_rate.rate = currency_rate.rate or currency_rate._get_latest_rate().rate or 1.0

    @api.depends('rate', 'name', 'currency_id', 'company_id', 'currency_id.rate_ids.rate')
    @api.depends_context('company')
    def _compute_company_rate(self):
        last_rate = self.env['res.currency.rate']._get_last_rates_for_companies(self.company_id | self.env.company.root_id)
        for currency_rate in self:
            company = currency_rate.company_id or self.env.company.root_id
            currency_rate.company_rate = (currency_rate.rate or currency_rate._get_latest_rate().rate or 1.0) / last_rate[company]

    @api.onchange('company_rate')
    def _inverse_company_rate(self):
        last_rate = self.env['res.currency.rate']._get_last_rates_for_companies(self.company_id | self.env.company.root_id)
        for currency_rate in self:
            company = currency_rate.company_id or self.env.company.root_id
            currency_rate.rate = currency_rate.company_rate * last_rate[company]

    @api.depends('company_rate')
    def _compute_inverse_company_rate(self):
        for currency_rate in self:
            if not currency_rate.company_rate:
                currency_rate.company_rate = 1.0
            currency_rate.inverse_company_rate = 1.0 / currency_rate.company_rate

    @api.onchange('inverse_company_rate')
    def _inverse_inverse_company_rate(self):
        for currency_rate in self:
            if not currency_rate.inverse_company_rate:
                currency_rate.inverse_company_rate = 1.0
            currency_rate.company_rate = 1.0 / currency_rate.inverse_company_rate

    @api.onchange('company_rate')
    def _onchange_rate_warning(self):
        latest_rate = self._get_latest_rate()
        if latest_rate:
            diff = (latest_rate.rate - self.rate) / latest_rate.rate
            if abs(diff) > 0.2:
                return {
                    'warning': {
                        'title': _("Warning for %s", self.currency_id.name),
                        'message': _(
                            "The new rate is quite far from the previous rate.\n"
                            "Incorrect currency rates may cause critical problems, make sure the rate is correct!"
                        )
                    }
                }

    @api.constrains('company_id')
    def _check_company_id(self):
        for rate in self:
            if rate.company_id.parent_id:
                raise ValidationError("Currency rates should only be created for main companies")

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        return super()._name_search(parse_date(self.env, name), domain, operator, limit, order)

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the rate field labels according to the company currency
        makes the view cache dependent on the company currency"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + ((self.env['res.company'].browse(self._context.get('company_id')) or self.env.company.root_id).currency_id.name,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type in ('tree'):
            names = {
                'company_currency_name': (self.env['res.company'].browse(self._context.get('company_id')) or self.env.company.root_id).currency_id.name,
                'rate_currency_name': self.env['res.currency'].browse(self._context.get('active_id')).name or 'Unit',
            }
            for field in [['company_rate', _('%(rate_currency_name)s per %(company_currency_name)s', **names)],
                          ['inverse_company_rate', _('%(company_currency_name)s per %(rate_currency_name)s', **names)]]:
                node = arch.xpath("//tree//field[@name='%s']" % field[0])
                if node:
                    node[0].set('string', field[1])
        return arch, view
