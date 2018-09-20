# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast
import itertools
import json
import locale
import logging
import os
import re
import tarfile
import tempfile
from collections import defaultdict
from operator import itemgetter
from io import BytesIO
from werkzeug.urls import url_join

import requests

from odoo import api, fields, models, http, tools, release, _
from odoo.modules import get_module_path, get_resource_path
from odoo.tools.misc import file_open, topological_sort
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

DEFAULT_DATE_FORMAT = '%m/%d/%Y'
DEFAULT_TIME_FORMAT = '%H:%M:%S'
MAX_FILE_SIZE = 15 * 1024 * 1024  # in megabytes


class Lang(models.Model):
    _name = "res.lang"
    _description = "Languages"
    _order = "active desc,name"

    _disallowed_datetime_patterns = list(tools.DATETIME_FORMATS_MAP)
    _disallowed_datetime_patterns.remove('%y') # this one is in fact allowed, just not good practice

    name = fields.Char(required=True)
    code = fields.Char(string='Locale Code', required=True, help='This field is used to set/get locales for user')
    iso_code = fields.Char(string='ISO code', help='This ISO code is the name of po files to use for translations')
    url_code = fields.Char('URL Code', required=True, help='The Lang Code displayed in the URL')
    active = fields.Boolean()
    direction = fields.Selection([('ltr', 'Left-to-Right'), ('rtl', 'Right-to-Left')], required=True, default='ltr')
    date_format = fields.Char(string='Date Format', required=True, default=DEFAULT_DATE_FORMAT)
    time_format = fields.Char(string='Time Format', required=True, default=DEFAULT_TIME_FORMAT)
    week_start = fields.Selection([('1', 'Monday'),
                                   ('2', 'Tuesday'),
                                   ('3', 'Wednesday'),
                                   ('4', 'Thursday'),
                                   ('5', 'Friday'),
                                   ('6', 'Saturday'),
                                   ('7', 'Sunday')], string='First Day of Week', required=True, default='7')
    grouping = fields.Char(string='Separator Format', required=True, default='[]',
        help="The Separator Format should be like [,n] where 0 < n :starting from Unit digit. "
             "-1 will end the separation. e.g. [3,2,-1] will represent 106500 to be 1,06,500; "
             "[1,2,-1] will represent it to be 106,50,0;[3] will represent it as 106,500. "
             "Provided ',' as the thousand separator in each case.")
    decimal_point = fields.Char(string='Decimal Separator', required=True, default='.', trim=False)
    thousands_sep = fields.Char(string='Thousands Separator', default=',', trim=False)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The name of the language must be unique !'),
        ('code_uniq', 'unique(code)', 'The code of the language must be unique !'),
        ('url_code_uniq', 'unique(url_code)', 'The URL code of the language must be unique !'),
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

    def _register_hook(self):
        # check that there is at least one active language
        if not self.search_count([]):
            _logger.error("No language is active.")

    # TODO remove me after v14
    def load_lang(self, lang, lang_name=None):
        _logger.warning("Call to deprecated method load_lang, use _create_lang or _activate_lang instead")
        language = self._activate_lang(lang) or self._create_lang(lang, lang_name)
        return language.id

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
            for pattern, replacement in tools.DATETIME_FORMATS_MAP.items():
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
            'grouping' : str(conv.get('grouping', [])),
        }
        try:
            return self.create(lang_info)
        finally:
            tools.resetlocale()

    @api.model
    def _get_i18n_url(self, base, lang):
        """ Generate the URL to fetch the translation resource
            e.g. https://nightly.odoo.com/i18n/13.0/fr.tar.xz
        """
        version = release.version.split('+')[0]  # remove +e part if present
        return url_join(base, "i18n/{}/{}.tar.xz".format(version, lang))

    @api.model
    def _extract_i18n_file_content(self, fileobj, lang, module_list):
        """ Extract the translations from the given archive

        The expected archive is a .tar.xz file using the structure:
            <module>/i18n/<lang>.po

        Regional variants are accepted (e.g. fr.tar.xz can contain both fr and
        fr_BE files)

        :param fileobj: a file object containing the compressed translation files
        :param lang: the language code to load (e.g. 'fr_FR')
        :param module_list: the list of modules to update from this archive
        """
        downloaded_addons = defaultdict(set)
        iso_code = tools.get_iso_codes(lang)
        base_lang_code = iso_code.split('_')[0] if '_' in iso_code else False

        with tarfile.open(mode='r:xz', fileobj=fileobj) as tar_content:
            with tempfile.TemporaryDirectory() as tmp:
                for member in tar_content.getmembers():

                    # sanity checks
                    if not member.isfile():
                        continue
                    if member.size > MAX_FILE_SIZE:
                        raise UserError(_("Content too long (got %.2fMB, max %.2fMB)") % (
                            member.size / (1024*1024),
                            MAX_FILE_SIZE / (1024*1024)
                        ))
                    filename = member.name
                    if not filename.endswith('.po'):
                        _logger.info("Skip unexpected file %s", filename)
                        continue

                    # TODO different separators for windows in tar?
                    addons = filename.split('/')[0]
                    if addons not in module_list:
                        # ensure a pack does not inject translations from another module
                        _logger.debug("Skip translations for unexpected module %s", addons)
                        continue

                    po_lang = filename.split('/')[-1][:-3]
                    if base_lang_code and po_lang == base_lang_code:
                        _logger.debug("Extracting base translation file %s to %s", filename, tmp)
                        downloaded_addons[base_lang_code].add(addons)
                        tar_content.extract(filename, path=tmp)
                        src_file = os.path.join(tmp, filename)
                        with open(src_file, 'rb') as po_file:
                            tools.trans_load_data(self._cr, po_file, 'po', base_lang_code, module_name=addons, verbose=False)

                    elif po_lang == iso_code:
                        _logger.debug("Extracting translation file %s to %s", filename, tmp)
                        downloaded_addons[iso_code].add(addons)
                        tar_content.extract(filename, path=tmp)
                        src_file = os.path.join(tmp, filename)
                        with open(src_file, 'rb') as po_file:
                            tools.trans_load_data(self._cr, po_file, 'po', iso_code, module_name=addons, verbose=False)
                    else:
                        _logger.debug("Skip translations for unexpected language %s", po_lang)
                        continue


        return downloaded_addons

    def _download_translation_files(self):
        """ Download the translation files of all modules from the i18n servers """
        mods = self.env['ir.module.module'].search_read([('state', '!=', 'uninstallable'),],
                                                        fields=['name', 'i18n_location'])
        # consider language packs are the most up to date, store the list of downloaded
        # module per language to check the filesystem only if was not found online
        processed = defaultdict(set)

        # [{'id': 1, 'name': 'base', 'i18n_location': 'https://...'},...] -> {'https://...': ['base',...],...}
        urls = defaultdict(list)
        for module_info in mods:
            urls[module_info['i18n_location']].append(module_info['name'])

        # ['fr_BE', 'fr_FR', 'nl_BE'] -> {'fr': ['fr_FR', 'fr_BE'], 'nl': ['nl_BE']}
        # will download once and process twice for self = [fr, fr_BE]
        langs = itertools.groupby(self.mapped('code'), key=lambda l: l.split('_')[0])
        for short_code, full_codes in langs:
            for url in urls:
                full_url = self._get_i18n_url(url, short_code)
                try:
                    stream = requests.get(full_url, timeout=5)
                    if stream.status_code != 200:
                        _logger.error("Could not fetch translations from %s, error code %s", full_url, stream.status_code)
                        continue

                    if int(stream.headers['content-length']) > MAX_FILE_SIZE:
                        raise UserError(_("Content too long (got %.2fMB, max %.2fMB)") % (
                            int(stream.headers['content-length']) / (1024*1024),
                            MAX_FILE_SIZE / (1024*1024)
                        ))
                    bio = BytesIO()
                    bio.write(stream.content)
                    bio.seek(0)
                    for full_code in list(full_codes):
                        for extracted_lang, modules in self._extract_i18n_file_content(bio, full_code, urls[url]).items():
                            processed[extracted_lang] |= modules
                except requests.exceptions.RequestException as err:
                    _logger.error("Could not fetch translations from %s, error: %s", full_url, err)
        return processed

    def _read_missing_from_fs(self, modules, to_skip):
        """ Read the filesystem for the languages and modules not yet processed

        :param self: list of res.lang records to process
        :param modules: list of module names to process
        :param to_skip: dict {lang: [modules]} containing the language code and modules
                        to skip as the translations were already retrieved
        """
        # TODO ensure no regression odoo/odoo#19824
        mod_dict = {
            mod.name: mod.dependencies_id.mapped('name')
            for mod in modules
        }
        mod_names = topological_sort(mod_dict)

        for lang in self:
            iso_code = tools.get_iso_codes(lang.code)
            base_lang_code = iso_code.split('_')[0] if '_' in iso_code else False

            for module in mod_names:

                path = get_module_path(module, display_warning=False)
                if not path:
                    # skip unknow modules, e.g. to_buy modules in community
                    continue

                # Step 1: for sub-languages, load base language first (e.g. es_CL.po is loaded over es.po)
                if base_lang_code and module not in to_skip.get(base_lang_code, []):
                    full_path = get_resource_path(path, 'i18n', base_lang_code + '.po')
                    if full_path:
                        with file_open(full_path, 'rb') as po_file:
                            _logger.info('module %s: loading base translation file (%s) for language %s', module, base_lang_code, lang.name)
                            tools.trans_load_data(self._cr, po_file, 'po', base_lang_code, module_name=module, verbose=False)

                if module in to_skip.get(iso_code, []):
                    continue

                # Step 2: then load the main translation file, possibly overriding the terms coming from the base language
                full_path = get_resource_path(path, 'i18n', iso_code + '.po')
                if full_path:
                    _logger.info('module %s: loading base translation file (%s) for language %s', module, iso_code, lang.name)
                    with file_open(full_path, 'rb') as po_file:
                        tools.trans_load_data(self._cr, po_file, 'po', lang.code, module_name=module, verbose=False)

    def _install_language(self, overwrite=False, remote=True):
        """
        Install/update a lang
        1. download language pack for all modules
        2. look into i18n/ folder for missing lang/module
        3. generate ir.translation on installed modules
        """
        for lang in self:
            self._activate_lang(lang.code)

        processed = {}
        if remote:
            processed = self._download_translation_files()

        mods = self.env['ir.module.module'].search([])
        self._read_missing_from_fs(mods, processed)

        mods._update_translations(filter_lang=self.mapped('code'), overwrite=overwrite)

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
        default_value = IrDefault.get('res.partner', 'lang')
        if default_value is None:
            IrDefault.set('res.partner', 'lang', lang_code)
            # set language of main company, created directly by db bootstrap SQL
            partner = self.env.company.partner_id
            if not partner.lang:
                partner.write({'lang': lang_code})
        return True

    @tools.ormcache('code')
    def _lang_get_id(self, code):
        return self.with_context(active_test=True).search([('code', '=', code)]).id

    @tools.ormcache('url_code')
    def _lang_get_code(self, url_code):
        return self.with_context(active_test=True).search([('url_code', '=', url_code)]).code or url_code

    def _lang_get(self, code):
        """ Return the language using this code if it is active """
        return self.browse(self._lang_get_id(code))

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
        return sorted([(lang.code, lang.url_code, lang.name) for lang in langs], key=itemgetter(2))

    @tools.ormcache('self.id')
    def _get_cached_values(self):
        self.ensure_one()
        return {
            'id': self.id,
            'code': self.code,
            'url_code': self.url_code,
            'name': self.name,
        }

    def _get_cached(self, field):
        return self._get_cached_values()[field]

    @api.model
    @tools.ormcache('code')
    def _lang_code_to_urlcode(self, code):
        for c, urlc, name in self.get_available():
            if c == code:
                return urlc
        return self._lang_get(code).url_code

    @api.model
    @tools.ormcache()
    def get_installed(self):
        """ Return the installed languages as a list of (code, name) sorted by name. """
        langs = self.with_context(active_test=True).search([])
        return sorted([(lang.code, lang.name) for lang in langs], key=itemgetter(1))

    def toggle_active(self):
        super().toggle_active()
        # Automatically load translation
        active_lang = [lang.code for lang in self.filtered(lambda l: l.active)]
        if active_lang:
            mods = self.env['ir.module.module'].search([('state', '=', 'installed')])
            mods._update_translations(active_lang)

    @api.model_create_multi
    def create(self, vals_list):
        self.clear_caches()
        for vals in vals_list:
            if not vals.get('url_code'):
                vals['url_code'] = vals.get('iso_code') or vals['code']
        return super(Lang, self).create(vals_list)

    def write(self, vals):
        lang_codes = self.mapped('code')
        if 'code' in vals and any(code != vals['code'] for code in lang_codes):
            raise UserError(_("Language code cannot be modified."))
        if vals.get('active') == False:
            if self.env['res.users'].search([('lang', 'in', lang_codes)]):
                raise UserError(_("Cannot deactivate a language that is currently used by users."))
            # delete linked ir.default specifying default partner's language
            self.env['ir.default'].discard_values('res.partner', 'lang', lang_codes)

        res = super(Lang, self).write(vals)
        self.flush()
        self.clear_caches()
        return res

    def unlink(self):
        for language in self:
            if language.code == 'en_US':
                raise UserError(_("Base Language 'en_US' can not be deleted."))
            ctx_lang = self._context.get('lang')
            if ctx_lang and (language.code == ctx_lang):
                raise UserError(_("You cannot delete the language which is the user's preferred language."))
            if language.active:
                raise UserError(_("You cannot delete the language which is Active!\nPlease de-activate the language first."))
            self.env['ir.translation'].search([('lang', '=', language.code)]).unlink()
        self.clear_caches()
        return super(Lang, self).unlink()

    def format(self, percent, value, grouping=False, monetary=False):
        """ Format() will return the language-specific output for float values"""
        self.ensure_one()
        if percent[0] != '%':
            raise ValueError(_("format() must be given exactly one %char format specifier"))

        formatted = percent % value

        # floats and decimal ints need special action!
        if grouping:
            lang_grouping, thousands_sep, decimal_point = self._data_get(monetary)
            eval_lang_grouping = ast.literal_eval(lang_grouping)

            if percent[-1] in 'eEfFgG':
                parts = formatted.split('.')
                parts[0] = intersperse(parts[0], eval_lang_grouping, thousands_sep)[0]

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
    res = separator.join(reverse(s) for s in reverse(splits))
    return left + res + right, len(splits) > 0 and len(splits) -1 or 0
