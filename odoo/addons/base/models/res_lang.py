# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import json
import locale
import logging
import re
from typing import Any, Literal

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import OrderedSet
from odoo.tools.misc import ReadonlyDict

_logger = logging.getLogger(__name__)

class LangData(ReadonlyDict):
    """ A ``dict``-like class which can access field value like a ``res.lang`` record.
    Note: This data class cannot store data for fields with the same name as
    ``dict`` methods, like ``dict.keys``.
    """
    __slots__ = ()

    def __bool__(self) -> bool:
        return bool(self.id)

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError


class LangDataDict(ReadonlyDict):
    """ A ``dict`` of :class:`LangData` objects indexed by some key, which returns
    a special dummy :class:`LangData` for missing keys.
    """
    __slots__ = ()

    def __getitem__(self, key: Any) -> LangData:
        try:
            return self._data__[key]
        except KeyError:
            some_lang = next(iter(self.values()))  # should have at least one active language
            return LangData(dict.fromkeys(some_lang, False))


class ResLang(models.Model):
    _name = 'res.lang'
    _description = "Languages"
    _order = "active desc,name"
    _allow_sudo_commands = False

    _disallowed_datetime_patterns = list(tools.misc.DATETIME_FORMATS_MAP)
    _disallowed_datetime_patterns.remove('%y') # this one is in fact allowed, just not good practice

    def _get_date_format_selection(self):
        current_year = fields.Date.today().year
        return [
            ('%d/%m/%Y', '31/01/%s' % current_year),
            ('%m/%d/%Y', '01/31/%s' % current_year),
            ('%Y/%m/%d', '%s/01/31' % current_year),
            ('%d-%m-%Y', '31-01-%s' % current_year),
            ('%m-%d-%Y', '01-31-%s' % current_year),
            ('%Y-%m-%d', '%s-01-31' % current_year),
            ('%d.%m.%Y', '31.01.%s' % current_year),
            ('%m.%d.%Y', '01.31.%s' % current_year),
            ('%Y.%m.%d', '%s.01.31' % current_year),
        ]

    name = fields.Char(required=True)
    code = fields.Char(string='Locale Code', required=True, help='This field is used to set/get locales for user')
    iso_code = fields.Char(string='ISO code', help='This ISO code is the name of po files to use for translations')
    url_code = fields.Char('URL Code', required=True, help='The Lang Code displayed in the URL')
    active = fields.Boolean()
    direction = fields.Selection([('ltr', 'Left-to-Right'), ('rtl', 'Right-to-Left')], required=True, default='ltr')
    date_format = fields.Selection(selection=_get_date_format_selection, string='Date Format', required=True, default='%m/%d/%Y')
    time_format = fields.Selection([
        ('%H:%M:%S', "13:00:00"),
        ('%I:%M:%S %p', " 1:00:00 PM"),
    ], string='Time Format', required=True, default='%H:%M:%S')
    week_start = fields.Selection([('1', 'Monday'),
                                   ('2', 'Tuesday'),
                                   ('3', 'Wednesday'),
                                   ('4', 'Thursday'),
                                   ('5', 'Friday'),
                                   ('6', 'Saturday'),
                                   ('7', 'Sunday')], string='First Day of Week', required=True, default='7')
    grouping = fields.Selection([
        ('[3,0]', 'International Grouping'),
        ('[3,2,0]', 'Indian Grouping'),
    ], string='Separator Format', required=True, default='[3,0]',
        help="The International Grouping will represent 123456789 to be 123,456,789.00; "
             "The Indian Grouping will represent 123456789 to be 12,34,56,789.00")
    decimal_point = fields.Char(string='Decimal Separator', required=True, default='.', trim=False)
    thousands_sep = fields.Char(string='Thousands Separator', default=',', trim=False)

    @api.depends('code', 'flag_image')
    def _compute_field_flag_image_url(self):
        for lang in self:
            if lang.flag_image:
                lang.flag_image_url = f"/web/image/res.lang/{lang.id}/flag_image"
            else:
                lang.flag_image_url = f"/base/static/img/country_flags/{lang.code.lower().rsplit('_')[-1]}.png"

    flag_image = fields.Image("Image")
    flag_image_url = fields.Char(compute=_compute_field_flag_image_url)

    _name_uniq = models.Constraint(
        'unique(name)',
        "The name of the language must be unique!",
    )
    _code_uniq = models.Constraint(
        'unique(code)',
        "The code of the language must be unique!",
    )
    _url_code_uniq = models.Constraint(
        'unique(url_code)',
        "The URL code of the language must be unique!",
    )

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

    @api.onchange('time_format', 'date_format')
    def _onchange_format(self):
        warning = {
            'warning': {
                'title': _("Using 24-hour clock format with AM/PM can cause issues."),
                'message': _("Changing to 12-hour clock format instead."),
                'type': 'notification'
            }
        }
        for lang in self:
            if lang.date_format and "%H" in lang.date_format and "%p" in lang.date_format:
                lang.date_format = lang.date_format.replace("%H", "%I")
                return warning
            if lang.time_format and "%H" in lang.time_format and "%p" in lang.time_format:
                lang.time_format = lang.time_format.replace("%H", "%I")
                return warning

    def _register_hook(self):
        # check that there is at least one active language
        if not self.search_count([]):
            _logger.error("No language is active.")

    def _activate_lang(self, code):
        """ Activate languages
        :param code: code of the language to activate
        :return: the language matching 'code' activated
        """
        lang = self.with_context(active_test=False).search([('code', '=', code)])
        if lang and not lang.active:
            lang.active = True
        return lang

    def _create_lang(self, lang, lang_name=None):
        """ Create the given language and make it active. """
        # create the language with locale information
        fail = True
        iso_lang = tools.get_iso_codes(lang)
        for ln in tools.translate.get_locales(lang):
            try:
                locale.setlocale(locale.LC_ALL, str(ln))
                fail = False
                break
            except locale.Error:
                continue
        if fail:
            lc = locale.getlocale()[0]
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
            for pattern, replacement in tools.misc.DATETIME_FORMATS_MAP.items():
                format = format.replace(pattern, replacement)
            return str(format)

        conv = locale.localeconv()
        lang_info = {
            'code': lang,
            'iso_code': iso_lang,
            'name': lang_name,
            'active': True,
            'date_format' : fix_datetime_format(locale.nl_langinfo(locale.D_FMT)),
            'time_format' : fix_datetime_format(locale.nl_langinfo(locale.T_FMT)),
            'decimal_point' : fix_xa0(str(conv['decimal_point'])),
            'thousands_sep' : fix_xa0(str(conv['thousands_sep'])),
            'grouping': str(conv.get('grouping') or '[3,0]'),
        }
        try:
            return self.create(lang_info)
        finally:
            tools.translate.resetlocale()

    @api.model
    def install_lang(self):
        """

        This method is called from odoo/addons/base/data/res_lang_data.xml to load
        some language and set it as the default for every partners. The
        language is set via tools.config by the '_initialize_db' method on the
        'db' object. This is a fragile solution and something else should be
        found.

        """
        # config['load_language'] is a comma-separated list or None
        lang_code = (tools.config.get('load_language') or 'en_US').split(',')[0]
        lang = self._activate_lang(lang_code) or self._create_lang(lang_code)
        IrDefault = self.env['ir.default']
        default_value = IrDefault._get('res.partner', 'lang')
        if default_value is None:
            IrDefault.set('res.partner', 'lang', lang_code)
            # set language of main company, created directly by db bootstrap SQL
            partner = self.env.company.partner_id
            if not partner.lang:
                partner.write({'lang': lang_code})
        return True

    # ------------------------------------------------------------
    # cached methods for **active** languages
    # ------------------------------------------------------------
    @property
    def CACHED_FIELDS(self) -> OrderedSet:
        """ Return fields to cache for the active languages
        Please promise all these fields don't depend on other models and context
        and are not translated.
        Warning: Don't add method names of ``dict`` to CACHED_FIELDS for sake of the
        implementation of LangData
        """
        return OrderedSet(['id', 'name', 'code', 'iso_code', 'url_code', 'active', 'direction', 'date_format',
                           'time_format', 'week_start', 'grouping', 'decimal_point', 'thousands_sep', 'flag_image_url'])

    def _get_data(self, **kwargs) -> LangData:
        """ Get the language data for the given field value in kwargs
        For example, get_data(code='en_US') will return the LangData
        for the res.lang record whose 'code' field value is 'en_US'

        :param dict kwargs: ``{field_name: field_value}``
                field_name is the only key in kwargs and in ``self.CACHED_FIELDS``
                Try to reuse the used ``field_name``: 'id', 'code', 'url_code'
        :return: Valid LangData if (field_name, field_value) pair is for an
                **active** language. Otherwise, Dummy LangData which will return
                ``False`` for all ``self.CACHED_FIELDS``
        :raise: UserError if field_name is not in ``self.CACHED_FIELDS``
        """
        [[field_name, field_value]] = kwargs.items()
        return self._get_active_by(field_name)[field_value]

    def _lang_get(self, code: str):
        """ Return the language using this code if it is active """
        return self.browse(self._get_data(code=code).id)

    def _get_code(self, code: str) -> str | Literal[False]:
        """ Return the given language code if active, else return ``False`` """
        return self._get_data(code=code).code

    @api.model
    @api.readonly
    def get_installed(self) -> list[tuple[str, str]]:
        """ Return installed languages' (code, name) pairs sorted by name. """
        return [(code, data.name) for code, data in self._get_active_by('code').items()]

    @tools.ormcache('field', cache='stable')
    def _get_active_by(self, field: str) -> LangDataDict:
        """ Return a LangDataDict mapping active languages' **unique**
        **required** ``self.CACHED_FIELDS`` values to their LangData.
        Its items are ordered by languages' names
        Try to reuse the used ``field``: 'id', 'code', 'url_code'
        """
        if field not in self.CACHED_FIELDS:
            raise UserError(_('Field "%s" is not cached', field))
        if field == 'code':
            langs = self.sudo().with_context(active_test=True).search_fetch([], self.CACHED_FIELDS, order='name')
            return LangDataDict({
                lang.code: LangData({f: lang[f] for f in self.CACHED_FIELDS})
                for lang in langs
            })
        return LangDataDict({data[field]: data for data in self._get_active_by('code').values()})

    # ------------------------------------------------------------

    def action_unarchive(self):
        activated = self.filtered(lambda rec: not rec.active)
        res = super(ResLang, activated).action_unarchive()
        # Automatically load translation
        if activated:
            active_lang = activated.mapped('code')
            mods = self.env['ir.module.module'].search([('state', '=', 'installed')])
            mods._update_translations(active_lang)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        self.env.registry.clear_cache('stable')
        for vals in vals_list:
            if not vals.get('url_code'):
                vals['url_code'] = vals.get('iso_code') or vals['code']
        return super().create(vals_list)

    def write(self, vals):
        lang_codes = self.mapped('code')
        if 'code' in vals and any(code != vals['code'] for code in lang_codes):
            raise UserError(_("Language code cannot be modified."))
        if vals.get('active') == False:
            if self.env['res.users'].with_context(active_test=True).search_count([('lang', 'in', lang_codes)], limit=1):
                raise UserError(_("Cannot deactivate a language that is currently used by users."))
            if self.env['res.partner'].with_context(active_test=True).search_count([('lang', 'in', lang_codes)], limit=1):
                raise UserError(_("Cannot deactivate a language that is currently used by contacts."))
            if self.env['res.users'].with_context(active_test=False).search_count([('lang', 'in', lang_codes)], limit=1):
                raise UserError(_("You cannot archive the language in which Odoo was setup as it is used by automated processes."))
            # delete linked ir.default specifying default partner's language
            self.env['ir.default'].discard_values('res.partner', 'lang', lang_codes)

        res = super().write(vals)

        if vals.get('active'):
            # If we activate a lang, set it's url_code to the shortest version
            # if possible
            for long_lang in self.filtered(lambda lang: '_' in lang.url_code):
                short_code = long_lang.code.split('_')[0]
                short_lang = self.with_context(active_test=False).search([
                    ('url_code', '=', short_code),
                ], limit=1)  # url_code is unique
                if (
                    short_lang
                    and not short_lang.active
                    # `code` should always be the long format containing `_` but
                    # there is a plan to change this in the future for `es_419`.
                    # This `and` is about not failing if it's the case one day.
                    and short_lang.code != short_code
                ):
                    short_lang.url_code = short_lang.code
                    long_lang.url_code = short_code

        self.env.flush_all()
        self.env.registry.clear_cache('stable')
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_except_default_lang(self):
        for language in self:
            if language.code == 'en_US':
                raise UserError(_("Base Language 'en_US' can not be deleted."))
            ctx_lang = self.env.context.get('lang')
            if ctx_lang and (language.code == ctx_lang):
                raise UserError(_("You cannot delete the language which is the user's preferred language."))
            if language.active:
                raise UserError(_("You cannot delete the language which is Active!\nPlease de-activate the language first."))

    def unlink(self):
        self.env.registry.clear_cache('stable')
        return super().unlink()

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for record, vals in zip(self, vals_list):
            if "name" not in default:
                vals["name"] = _("%s (copy)", record.name)
            if "code" not in default:
                vals["code"] = _("%s (copy)", record.code)
            if "url_code" not in default:
                vals["url_code"] = _("%s (copy)", record.url_code)
        return vals_list

    def format(self, percent: str, value, grouping: bool = False) -> str:
        """ Format() will return the language-specific output for float values"""
        self.ensure_one()
        if percent[0] != '%':
            raise ValueError(_("format() must be given exactly one %char format specifier"))

        formatted = percent % value

        data = self._get_data(id=self.id)
        if not data:
            raise UserError(_("The language %s is not installed.", self.name))
        decimal_point = data.decimal_point
        # floats and decimal ints need special action!
        if grouping:
            lang_grouping, thousands_sep = data.grouping, data.thousands_sep or ''
            eval_lang_grouping = ast.literal_eval(lang_grouping)

            if percent[-1] in 'eEfFgG':
                parts = formatted.split('.')
                parts[0] = intersperse(parts[0], eval_lang_grouping, thousands_sep)[0]

                formatted = decimal_point.join(parts)

            elif percent[-1] in 'diu':
                formatted = intersperse(formatted, eval_lang_grouping, thousands_sep)[0]

        elif percent[-1] in 'eEfFgG' and '.' in formatted:
            formatted = formatted.replace('.', decimal_point)

        return formatted

    def action_activate_langs(self):
        """ Activate the selected languages """
        self.action_unarchive()
        message = _("The languages that you selected have been successfully installed. Users can choose their favorite language in their preferences.")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'target': 'new',
            'params': {
                'message': message,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

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
    res = separator.join(reverse(s) for s in reverse(splits))
    return left + res + right, len(splits) > 0 and len(splits) -1 or 0
