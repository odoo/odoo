# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import locale
from locale import localeconv
import logging
import re

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _
from openerp.exceptions import UserError

_logger = logging.getLogger(__name__)

class lang(osv.osv):
    _name = "res.lang"
    _description = "Languages"

    _disallowed_datetime_patterns = tools.DATETIME_FORMATS_MAP.keys()
    _disallowed_datetime_patterns.remove('%y') # this one is in fact allowed, just not good practice

    def install_lang(self, cr, uid, **args):
        """

        This method is called from openerp/addons/base/base_data.xml to load
        some language and set it as the default for every partners. The
        language is set via tools.config by the RPC 'create' method on the
        'db' object. This is a fragile solution and something else should be
        found.

        """
        lang = tools.config.get('lang')
        if not lang:
            return False
        lang_ids = self.search(cr, uid, [('code','=', lang)])
        if not lang_ids:
            self.load_lang(cr, uid, lang)
        ir_values_obj = self.pool.get('ir.values')
        default_value = ir_values_obj.get(cr, uid, 'default', False, ['res.partner'])
        if not default_value:
            ir_values_obj.set(cr, uid, 'default', False, 'lang', ['res.partner'], lang)
        return True

    def load_lang(self, cr, uid, lang, lang_name=None):
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
            lang_name = tools.ALL_LANGUAGES.get(lang, lang)


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
            'translatable': 1,
            'date_format' : fix_datetime_format(locale.nl_langinfo(locale.D_FMT)),
            'time_format' : fix_datetime_format(locale.nl_langinfo(locale.T_FMT)),
            'decimal_point' : fix_xa0(str(conv['decimal_point'])),
            'thousands_sep' : fix_xa0(str(conv['thousands_sep'])),
            'grouping' : str(conv.get('grouping', [])),
        }
        lang_id = False
        try:
            lang_id = self.create(cr, uid, lang_info)
        finally:
            tools.resetlocale()
        return lang_id

    def _check_format(self, cr, uid, ids, context=None):
        for lang in self.browse(cr, uid, ids, context=context):
            for pattern in self._disallowed_datetime_patterns:
                if (lang.time_format and pattern in lang.time_format)\
                    or (lang.date_format and pattern in lang.date_format):
                    return False
        return True

    def _check_grouping(self, cr, uid, ids, context=None):
        for lang in self.browse(cr, uid, ids, context=context):
            try:
                if not all(isinstance(x, int) for x in eval(lang.grouping)):
                    return False
            except Exception:
                return False
        return True

    def _get_default_date_format(self, cursor, user, context=None):
        return '%m/%d/%Y'

    def _get_default_time_format(self, cursor, user, context=None):
        return '%H:%M:%S'

    _columns = {
        'name': fields.char('Name', required=True),
        'code': fields.char('Locale Code', size=16, required=True, help='This field is used to set/get locales for user'),
        'iso_code': fields.char('ISO code', size=16, required=False, help='This ISO code is the name of po files to use for translations'),
        'translatable': fields.boolean('Translatable'),
        'active': fields.boolean('Active'),
        'direction': fields.selection([('ltr', 'Left-to-Right'), ('rtl', 'Right-to-Left')], 'Direction', required=True),
        'date_format':fields.char('Date Format', required=True),
        'time_format':fields.char('Time Format', required=True),
        'grouping':fields.char('Separator Format', required=True,help="The Separator Format should be like [,n] where 0 < n :starting from Unit digit.-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500;[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. Provided ',' as the thousand separator in each case."),
        'decimal_point':fields.char('Decimal Separator', required=True),
        'thousands_sep':fields.char('Thousands Separator'),
    }
    _defaults = {
        'active': 1,
        'translatable': 0,
        'direction': 'ltr',
        'date_format':_get_default_date_format,
        'time_format':_get_default_time_format,
        'grouping': '[3, 0]',
        'decimal_point': '.',
        'thousands_sep': ',',
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the language must be unique !'),
        ('code_uniq', 'unique (code)', 'The code of the language must be unique !'),
    ]

    _constraints = [
        (_check_format, 'Invalid date/time format directive specified. Please refer to the list of allowed directives, displayed when you edit a language.', ['time_format', 'date_format']),
        (_check_grouping, "The Separator Format should be like [,n] where 0 < n :starting from Unit digit.-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500;[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. Provided ',' as the thousand separator in each case.", ['grouping'])
    ]

    @tools.ormcache('lang')
    def _lang_get(self, cr, uid, lang):
        lang_ids = self.search(cr, uid, [('code', '=', lang)]) or \
                   self.search(cr, uid, [('code', '=', 'en_US')])
        return lang_ids[0]

    @tools.ormcache('lang', 'monetary')
    def _lang_data_get(self, cr, uid, lang, monetary=False):
        if type(lang) in (str, unicode):
            lang = self._lang_get(cr, uid, lang)
        conv = localeconv()
        lang_obj = self.browse(cr, uid, lang)
        thousands_sep = lang_obj.thousands_sep or conv[monetary and 'mon_thousands_sep' or 'thousands_sep']
        decimal_point = lang_obj.decimal_point
        grouping = lang_obj.grouping
        return grouping, thousands_sep, decimal_point

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
             ids = [ids]

        if 'code' in vals:
            for rec in self.browse(cr, uid, ids, context):
                if rec.code != vals['code']:
                    raise UserError(_("Language code cannot be modified."))

        if vals.get('active') == False:
            users = self.pool.get('res.users')
            if self.search_count(cr, uid, [('id', 'in', ids), ('code', '=', 'en_US')], context=context):
                raise UserError(_("Base Language 'en_US' can not be deactivated!"))

            for current_id in ids:
                current_language = self.browse(cr, uid, current_id, context=context)
                if users.search(cr, uid, [('lang', '=', current_language.code)], context=context):
                    raise UserError(_("Cannot unactivate a language that is currently used by users."))

        self._lang_get.clear_cache(self)
        self._lang_data_get.clear_cache(self)
        return super(lang, self).write(cr, uid, ids, vals, context)

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        languages = self.read(cr, uid, ids, ['code','active'], context=context)
        for language in languages:
            ctx_lang = context.get('lang')
            if language['code']=='en_US':
                raise UserError(_("Base Language 'en_US' can not be deleted!"))
            if ctx_lang and (language['code']==ctx_lang):
                raise UserError(_("You cannot delete the language which is User's Preferred Language!"))
            if language['active']:
                raise UserError(_("You cannot delete the language which is Active!\nPlease de-activate the language first."))
            trans_obj = self.pool.get('ir.translation')
            trans_ids = trans_obj.search(cr, uid, [('lang','=',language['code'])], context=context)
            trans_obj.unlink(cr, uid, trans_ids, context=context)
        self._lang_get.clear_cache(self)
        self._lang_data_get.clear_cache(self)
        return super(lang, self).unlink(cr, uid, ids, context=context)

    #
    # IDS: can be a list of IDS or a list of XML_IDS
    #
    def format(self, cr, uid, ids, percent, value, grouping=False, monetary=False, context=None):
        """ Format() will return the language-specific output for float values"""
        if percent[0] != '%':
            raise ValueError("format() must be given exactly one %char format specifier")

        formatted = percent % value

        # floats and decimal ints need special action!
        if grouping:
            lang_grouping, thousands_sep, decimal_point = \
                self._lang_data_get(cr, uid, ids[0], monetary)
            eval_lang_grouping = eval(lang_grouping)

            if percent[-1] in 'eEfFgG':
                parts = formatted.split('.')
                parts[0], _ = intersperse(parts[0], eval_lang_grouping, thousands_sep)

                formatted = decimal_point.join(parts)

            elif percent[-1] in 'diu':
                formatted = intersperse(formatted, eval_lang_grouping, thousands_sep)[0]

        return formatted

#    import re, operator
#    _percent_re = re.compile(r'%(?:\((?P<key>.*?)\))?'
#                             r'(?P<modifiers>[-#0-9 +*.hlL]*?)[eEfFgGdiouxXcrs%]')

lang()

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
