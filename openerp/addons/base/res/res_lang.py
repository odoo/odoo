# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import locale
import logging
import re
from operator import itemgetter

from odoo import api, fields, models, tools, _
from odoo.tools.safe_eval import safe_eval as eval
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

DEFAULT_DATE_FORMAT = '%m/%d/%Y'
DEFAULT_TIME_FORMAT = '%H:%M:%S'


class Lang(models.Model):
    _name = "res.lang"
    _description = "Languages"
    _order = "active desc,name"

    _disallowed_datetime_patterns = tools.DATETIME_FORMATS_MAP.keys()
    _disallowed_datetime_patterns.remove('%y') # this one is in fact allowed, just not good practice

    name = fields.Char(required=True)
    code = fields.Char(string='Locale Code', required=True, help='This field is used to set/get locales for user')
    iso_code = fields.Char(string='ISO code', help='This ISO code is the name of po files to use for translations')
    translatable = fields.Boolean()
    active = fields.Boolean()
    direction = fields.Selection([('ltr', 'Left-to-Right'), ('rtl', 'Right-to-Left')], required=True, default='ltr')
    date_format = fields.Char(string='Date Format', required=True, default=DEFAULT_DATE_FORMAT)
    time_format = fields.Char(string='Time Format', required=True, default=DEFAULT_TIME_FORMAT)
    grouping = fields.Char(string='Separator Format', required=True, default='[]',
        help="The Separator Format should be like [,n] where 0 < n :starting from Unit digit. "
             "-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500; "
             "[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. "
             "Provided ',' as the thousand separator in each case.")
    decimal_point = fields.Char(string='Decimal Separator', required=True, default='.')
    thousands_sep = fields.Char(string='Thousands Separator', default=',')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The name of the language must be unique !'),
        ('code_uniq', 'unique(code)', 'The code of the language must be unique !'),
    ]

    @api.constrains('active')
    def _check_active(self):
        # do not check during installation
        if self.env.registry.ready and not self.search_count([]):
            raise ValidationError(_('At least one language must be active.'))

    @api.constrains('time_format', 'date_format')
    def _check_format(self):
        for lang in self:
            for pattern in lang._disallowed_datetime_patterns:
                if (lang.time_format and pattern in lang.time_format) or \
                        (lang.date_format and pattern in lang.date_format):
                    raise ValidationError(_('Invalid date/time format directive specified. '
                                            'Please refer to the list of allowed directives, '
                                            'displayed when you edit a language.'))

    @api.constrains('grouping')
    def _check_grouping(self):
        warning = _('The Separator Format should be like [,n] where 0 < n :starting from Unit digit. '
                    '-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500;'
                    '[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. '
                    'Provided as the thousand separator in each case.')
        for lang in self:
            try:
                if not all(isinstance(x, int) for x in json.loads(lang.grouping)):
                    raise ValidationError(warning)
            except Exception:
                raise ValidationError(warning)

    @api.model_cr
    def _register_hook(self):
        # check that there is at least one active language
        if not self.search_count([]):
            _logger.error("No language is active.")

    @api.model
    def load_lang(self, lang, lang_name=None):
        """ Create the given language if necessary, and make it active. """
        # if the language exists, simply make it active
        language = self.with_context(active_test=False).search([('code', '=', lang)], limit=1)
        if language:
            language.write({'active': True})
            return language.id

        # create the language with locale information
        fail = True
        iso_lang = tools.get_iso_codes(lang)
        for ln in tools.get_locales(lang):
            try:
                locale.setlocale(locale.LC_ALL, str(ln))
                fail = False
                break
            except locale.Error:
                continue
        if fail:
            lc = locale.getdefaultlocale()[0]
            msg = 'Unable to get information for locale %s. Information from the default locale (%s) have been used.'
            _logger.warning(msg, lang, lc)

        if not lang_name:
            lang_name = lang

        def fix_xa0(s):
            """Fix badly-encoded non-breaking space Unicode character from locale.localeconv(),
               coercing to utf-8, as some platform seem to output localeconv() in their system
               encoding, e.g. Windows-1252"""
            if s == '\xa0':
                return '\xc2\xa0'
            return s

        def fix_datetime_format(format):
            """Python's strftime supports only the format directives
               that are available on the platform's libc, so in order to
               be 100% cross-platform we map to the directives required by
               the C standard (1989 version), always available on platforms
               with a C standard implementation."""
            # For some locales, nl_langinfo returns a D_FMT/T_FMT that contains
            # unsupported '%-' patterns, e.g. for cs_CZ
            format = format.replace('%-', '%')
            for pattern, replacement in tools.DATETIME_FORMATS_MAP.iteritems():
                format = format.replace(pattern, replacement)
            return str(format)

        conv = locale.localeconv()
        lang_info = {
            'code': lang,
            'iso_code': iso_lang,
            'name': lang_name,
            'active': True,
            'translatable': True,
            'date_format' : fix_datetime_format(locale.nl_langinfo(locale.D_FMT)),
            'time_format' : fix_datetime_format(locale.nl_langinfo(locale.T_FMT)),
            'decimal_point' : fix_xa0(str(conv['decimal_point'])),
            'thousands_sep' : fix_xa0(str(conv['thousands_sep'])),
            'grouping' : str(conv.get('grouping', [])),
        }
        try:
            return self.create(lang_info).id
        finally:
            tools.resetlocale()

    @api.model
    def install_lang(self):
        """

        This method is called from openerp/addons/base/base_data.xml to load
        some language and set it as the default for every partners. The
        language is set via tools.config by the RPC 'create' method on the
        'db' object. This is a fragile solution and something else should be
        found.

        """
        # config['load_language'] is a comma-separated list or None
        lang_code = (tools.config.get('load_language') or 'en_US').split(',')[0]
        lang = self.search([('code', '=', lang_code)])
        if not lang:
            self.load_lang(lang_code)
        IrValues = self.env['ir.values']
        default_value = IrValues.get_defaults('res.partner', condition=False)
        if not default_value:
            IrValues.set_default('res.partner', 'lang', lang_code, condition=False)
            # set language of main company, created directly by db bootstrap SQL
            partner = self.env.user.company_id.partner_id
            if not partner.lang:
                partner.write({'lang': lang_code})
        return True

    @tools.ormcache('code')
    def _lang_get_id(self, code):
        return (self.search([('code', '=', code)]) or
                self.search([('code', '=', 'en_US')]) or
                self.search([], limit=1)).id

    @api.model
    @api.returns('self', lambda value: value.id)
    def _lang_get(self, code):
        return self.browse(self._lang_get_id(code))

    @api.v7
    def _lang_data_get(self, cr, uid, lang, monetary=False):
        if isinstance(lang, basestring):
            lang = self._lang_get(cr, uid, lang)
        return self.browse(cr, uid, lang)._data_get(monetary)

    @tools.ormcache('self.code', 'monetary')
    def _data_get(self, monetary=False):
        conv = locale.localeconv()
        thousands_sep = self.thousands_sep or conv[monetary and 'mon_thousands_sep' or 'thousands_sep']
        decimal_point = self.decimal_point
        grouping = self.grouping
        return grouping, thousands_sep, decimal_point

    @api.model
    @tools.ormcache()
    def get_available(self):
        """ Return the available languages as a list of (code, name) sorted by name. """
        langs = self.with_context(active_test=False).search([])
        return sorted([(lang.code, lang.name) for lang in langs], key=itemgetter(1))

    @api.model
    @tools.ormcache()
    def get_installed(self):
        """ Return the installed languages as a list of (code, name) sorted by name. """
        langs = self.with_context(active_test=True).search([])
        return sorted([(lang.code, lang.name) for lang in langs], key=itemgetter(1))

    @api.model
    def create(self, vals):
        self.clear_caches()
        return super(Lang, self).create(vals)

    @api.multi
    def write(self, vals):
        lang_codes = self.mapped('code')
        if 'code' in vals and any(code != vals['code'] for code in lang_codes):
            raise UserError(_("Language code cannot be modified."))
        if vals.get('active') == False and self.env['res.users'].search([('lang', 'in', lang_codes)]):
            raise UserError(_("Cannot unactivate a language that is currently used by users."))
        self.clear_caches()
        return super(Lang, self).write(vals)

    @api.multi
    def unlink(self):
        for language in self:
            if language.code == 'en_US':
                raise UserError(_("Base Language 'en_US' can not be deleted!"))
            ctx_lang = self._context.get('lang')
            if ctx_lang and (language.code == ctx_lang):
                raise UserError(_("You cannot delete the language which is User's Preferred Language!"))
            if language.active:
                raise UserError(_("You cannot delete the language which is Active!\nPlease de-activate the language first."))
            self.env['ir.translation'].search([('lang', '=', language.code)]).unlink()
        self.clear_caches()
        return super(Lang, self).unlink()

    #
    # IDS: can be a list of IDS or a list of XML_IDS
    #
    @api.v7
    def format(self, cr, uid, ids, percent, value, grouping=False, monetary=False, context=None):
        # Refering the old code, `ids` is expected to have only one value(ID or XML_ID) inside list, hence used ids[0].
        lang_id = ids[0]
        if isinstance(lang_id, (str, unicode)):
            lang_id = self._lang_get(cr, uid, lang_id)
        lang = self.browse(cr, uid, lang_id, context=context)
        return Lang.format(lang, percent, value, grouping=grouping, monetary=monetary)

    @api.v8
    def format(self, percent, value, grouping=False, monetary=False):
        """ Format() will return the language-specific output for float values"""
        self.ensure_one()
        if percent[0] != '%':
            raise ValueError(_("format() must be given exactly one %char format specifier"))

        formatted = percent % value

        # floats and decimal ints need special action!
        if grouping:
            lang_grouping, thousands_sep, decimal_point = self._data_get(monetary)
            eval_lang_grouping = eval(lang_grouping)

            if percent[-1] in 'eEfFgG':
                parts = formatted.split('.')
                parts[0], _ = intersperse(parts[0], eval_lang_grouping, thousands_sep)

                formatted = decimal_point.join(parts)

            elif percent[-1] in 'diu':
                formatted = intersperse(formatted, eval_lang_grouping, thousands_sep)[0]

        return formatted


def split(l, counts):
    """

    >>> split("hello world", [])
    ['hello world']
    >>> split("hello world", [1])
    ['h', 'ello world']
    >>> split("hello world", [2])
    ['he', 'llo world']
    >>> split("hello world", [2,3])
    ['he', 'llo', ' world']
    >>> split("hello world", [2,3,0])
    ['he', 'llo', ' wo', 'rld']
    >>> split("hello world", [2,-1,3])
    ['he', 'llo world']

    """
    res = []
    saved_count = len(l) # count to use when encoutering a zero
    for count in counts:
        if not l:
            break
        if count == -1:
            break
        if count == 0:
            while l:
                res.append(l[:saved_count])
                l = l[saved_count:]
            break
        res.append(l[:count])
        l = l[count:]
        saved_count = count
    if l:
        res.append(l)
    return res

intersperse_pat = re.compile('([^0-9]*)([^ ]*)(.*)')

def intersperse(string, counts, separator=''):
    """

    See the asserts below for examples.

    """
    left, rest, right = intersperse_pat.match(string).groups()
    def reverse(s): return s[::-1]
    splits = split(reverse(rest), counts)
    res = separator.join(map(reverse, reverse(splits)))
    return left + res + right, len(splits) > 0 and len(splits) -1 or 0
