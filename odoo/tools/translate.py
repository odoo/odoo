# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from __future__ import annotations

import codecs
import fnmatch
import functools
import inspect
import io
import itertools
import json
import locale
import logging
import os
from tokenize import generate_tokens, STRING, NEWLINE, INDENT, DEDENT
import polib
import re
import tarfile
import threading
import warnings
from collections import defaultdict, namedtuple
from contextlib import suppress
from datetime import datetime
from os.path import join

from pathlib import Path
from babel.messages import extract
from lxml import etree, html
from markupsafe import escape, Markup
from psycopg2.extras import Json

import odoo
from odoo.exceptions import UserError
from . import config, pycompat
from .misc import file_open, file_path, get_iso_codes, SKIPPED_ELEMENT_TYPES

_logger = logging.getLogger(__name__)

PYTHON_TRANSLATION_COMMENT = 'odoo-python'

# translation used for javascript code in web client
JAVASCRIPT_TRANSLATION_COMMENT = 'odoo-javascript'
# used to notify web client that these translations should be loaded in the UI
# deprecated comment since Odoo 16.0
WEB_TRANSLATION_COMMENT = "openerp-web"

SKIPPED_ELEMENTS = ('script', 'style', 'title')

_LOCALE2WIN32 = {
    'af_ZA': 'Afrikaans_South Africa',
    'sq_AL': 'Albanian_Albania',
    'ar_SA': 'Arabic_Saudi Arabia',
    'eu_ES': 'Basque_Spain',
    'be_BY': 'Belarusian_Belarus',
    'bs_BA': 'Bosnian_Bosnia and Herzegovina',
    'bg_BG': 'Bulgarian_Bulgaria',
    'ca_ES': 'Catalan_Spain',
    'hr_HR': 'Croatian_Croatia',
    'zh_CN': 'Chinese_China',
    'zh_TW': 'Chinese_Taiwan',
    'cs_CZ': 'Czech_Czech Republic',
    'da_DK': 'Danish_Denmark',
    'nl_NL': 'Dutch_Netherlands',
    'et_EE': 'Estonian_Estonia',
    'fa_IR': 'Farsi_Iran',
    'ph_PH': 'Filipino_Philippines',
    'fi_FI': 'Finnish_Finland',
    'fr_FR': 'French_France',
    'fr_BE': 'French_France',
    'fr_CH': 'French_France',
    'fr_CA': 'French_France',
    'ga': 'Scottish Gaelic',
    'gl_ES': 'Galician_Spain',
    'ka_GE': 'Georgian_Georgia',
    'de_DE': 'German_Germany',
    'el_GR': 'Greek_Greece',
    'gu': 'Gujarati_India',
    'he_IL': 'Hebrew_Israel',
    'hi_IN': 'Hindi',
    'hu': 'Hungarian_Hungary',
    'is_IS': 'Icelandic_Iceland',
    'id_ID': 'Indonesian_Indonesia',
    'it_IT': 'Italian_Italy',
    'ja_JP': 'Japanese_Japan',
    'kn_IN': 'Kannada',
    'km_KH': 'Khmer',
    'ko_KR': 'Korean_Korea',
    'lo_LA': 'Lao_Laos',
    'lt_LT': 'Lithuanian_Lithuania',
    'lat': 'Latvian_Latvia',
    'ml_IN': 'Malayalam_India',
    'mi_NZ': 'Maori',
    'mn': 'Cyrillic_Mongolian',
    'no_NO': 'Norwegian_Norway',
    'nn_NO': 'Norwegian-Nynorsk_Norway',
    'pl': 'Polish_Poland',
    'pt_PT': 'Portuguese_Portugal',
    'pt_BR': 'Portuguese_Brazil',
    'ro_RO': 'Romanian_Romania',
    'ru_RU': 'Russian_Russia',
    'sr_CS': 'Serbian (Cyrillic)_Serbia and Montenegro',
    'sk_SK': 'Slovak_Slovakia',
    'sl_SI': 'Slovenian_Slovenia',
    #should find more specific locales for Spanish countries,
    #but better than nothing
    'es_AR': 'Spanish_Spain',
    'es_BO': 'Spanish_Spain',
    'es_CL': 'Spanish_Spain',
    'es_CO': 'Spanish_Spain',
    'es_CR': 'Spanish_Spain',
    'es_DO': 'Spanish_Spain',
    'es_EC': 'Spanish_Spain',
    'es_ES': 'Spanish_Spain',
    'es_GT': 'Spanish_Spain',
    'es_HN': 'Spanish_Spain',
    'es_MX': 'Spanish_Spain',
    'es_NI': 'Spanish_Spain',
    'es_PA': 'Spanish_Spain',
    'es_PE': 'Spanish_Spain',
    'es_PR': 'Spanish_Spain',
    'es_PY': 'Spanish_Spain',
    'es_SV': 'Spanish_Spain',
    'es_UY': 'Spanish_Spain',
    'es_VE': 'Spanish_Spain',
    'sv_SE': 'Swedish_Sweden',
    'ta_IN': 'English_Australia',
    'th_TH': 'Thai_Thailand',
    'tr_TR': 'Turkish_Türkiye',
    'uk_UA': 'Ukrainian_Ukraine',
    'vi_VN': 'Vietnamese_Viet Nam',
    'tlh_TLH': 'Klingon',

}

# these direct uses of CSV are ok.
import csv # pylint: disable=deprecated-module
class UNIX_LINE_TERMINATOR(csv.excel):
    lineterminator = '\n'

csv.register_dialect("UNIX", UNIX_LINE_TERMINATOR)


# FIXME: holy shit this whole thing needs to be cleaned up hard it's a mess
def encode(s):
    assert isinstance(s, str)
    return s


# which elements are translated inline
TRANSLATED_ELEMENTS = {
    'abbr', 'b', 'bdi', 'bdo', 'br', 'cite', 'code', 'data', 'del', 'dfn', 'em',
    'font', 'i', 'ins', 'kbd', 'keygen', 'mark', 'math', 'meter', 'output',
    'progress', 'q', 'ruby', 's', 'samp', 'small', 'span', 'strong', 'sub',
    'sup', 'time', 'u', 'var', 'wbr', 'text', 'select', 'option',
}

# Which attributes must be translated. This is a dict, where the value indicates
# a condition for a node to have the attribute translatable.
# ⚠ Note that it implicitly includes their t-attf-* equivalent.
TRANSLATED_ATTRS = dict.fromkeys({
    'string', 'add-label', 'help', 'sum', 'avg', 'confirm', 'placeholder', 'alt', 'title', 'aria-label',
    'aria-keyshortcuts', 'aria-placeholder', 'aria-roledescription', 'aria-valuetext',
    'value_label', 'data-tooltip', 'data-editor-message', 'label', 'cancel-label', 'confirm-label',
}, lambda e: True)

def translate_attrib_value(node):
    # check if the value attribute of a node must be translated
    classes = node.attrib.get('class', '').split(' ')
    return (
        (node.tag == 'input' and node.attrib.get('type', 'text') == 'text')
        and 'datetimepicker-input' not in classes
        or (node.tag == 'input' and node.attrib.get('type') == 'hidden')
        and 'o_translatable_input_hidden' in classes
    )

TRANSLATED_ATTRS.update(
    value=translate_attrib_value,
    text=lambda e: (e.tag == 'field' and e.attrib.get('widget', '') == 'url'),
    **{f't-attf-{attr}': cond for attr, cond in TRANSLATED_ATTRS.items()},
)

# This should match the list provided to OWL (see translatableAttributes).
OWL_TRANSLATED_ATTRS = {
    "alt",
    "aria-label",
    "aria-placeholder",
    "aria-roledescription",
    "aria-valuetext",
    "data-tooltip",
    "label",
    "placeholder",
    "title",
}

avoid_pattern = re.compile(r"\s*<!DOCTYPE", re.IGNORECASE | re.MULTILINE | re.UNICODE)
space_pattern = re.compile(r"[\s\uFEFF]*")  # web_editor uses \uFEFF as ZWNBSP


def translate_xml_node(node, callback, parse, serialize):
    """ Return the translation of the given XML/HTML node.

        :param node:
        :param callback: callback(text) returns translated text or None
        :param parse: parse(text) returns a node (text is unicode)
        :param serialize: serialize(node) returns unicode text
    """

    def nonspace(text):
        """ Return whether ``text`` is a string with non-space characters. """
        return bool(text) and not space_pattern.fullmatch(text)

    def translatable(node):
        """ Return whether the given node can be translated as a whole. """
        return (
            # Some specific nodes (e.g., text highlights) have an auto-updated
            # DOM structure that makes them impossible to translate.
            # The introduction of a translation `<span>` in the middle of their
            # hierarchy breaks their functionalities. We need to force them to
            # be translated as a whole using the `o_translate_inline` class.
            "o_translate_inline" in node.attrib.get("class", "").split()
            or node.tag in TRANSLATED_ELEMENTS
            and not any(key.startswith("t-") for key in node.attrib)
            and all(translatable(child) for child in node)
        )

    def hastext(node, pos=0):
        """ Return whether the given node contains some text to translate at the
            given child node position.  The text may be before the child node,
            inside it, or after it.
        """
        return (
            # there is some text before node[pos]
            nonspace(node[pos-1].tail if pos else node.text)
            or (
                pos < len(node)
                and translatable(node[pos])
                and (
                    any(  # attribute to translate
                        val and key in TRANSLATED_ATTRS and TRANSLATED_ATTRS[key](node[pos])
                        for key, val in node[pos].attrib.items()
                    )
                    # node[pos] contains some text to translate
                    or hastext(node[pos])
                    # node[pos] has no text, but there is some text after it
                    or hastext(node, pos + 1)
                )
            )
        )

    def process(node):
        """ Translate the given node. """
        if (
            isinstance(node, SKIPPED_ELEMENT_TYPES)
            or node.tag in SKIPPED_ELEMENTS
            or node.get('t-translation', "").strip() == "off"
            or node.tag == 'attribute' and node.get('name') not in TRANSLATED_ATTRS
            or node.getparent() is None and avoid_pattern.match(node.text or "")
        ):
            return

        pos = 0
        while True:
            # check for some text to translate at the given position
            if hastext(node, pos):
                # move all translatable children nodes from the given position
                # into a <div> element
                div = etree.Element('div')
                div.text = (node[pos-1].tail if pos else node.text) or ''
                while pos < len(node) and translatable(node[pos]):
                    div.append(node[pos])

                # translate the content of the <div> element as a whole
                content = serialize(div)[5:-6]
                original = content.strip()
                translated = callback(original)
                if translated:
                    result = content.replace(original, translated)
                    # <div/> is used to auto fix crapy result
                    result_elem = parse_html(f"<div>{result}</div>")
                    # change the tag to <span/> which is one of TRANSLATED_ELEMENTS
                    # so that 'result_elem' can be checked by translatable and hastext
                    result_elem.tag = 'span'
                    if translatable(result_elem) and hastext(result_elem):
                        div = result_elem
                        if pos:
                            node[pos-1].tail = div.text
                        else:
                            node.text = div.text

                # move the content of the <div> element back inside node
                while len(div) > 0:
                    node.insert(pos, div[0])
                    pos += 1

            if pos >= len(node):
                break

            # node[pos] is not translatable as a whole, process it recursively
            process(node[pos])
            pos += 1

        # translate the attributes of the node
        for key, val in node.attrib.items():
            if nonspace(val) and key in TRANSLATED_ATTRS and TRANSLATED_ATTRS[key](node):
                node.set(key, callback(val.strip()) or val)

    process(node)

    return node


def parse_xml(text):
    return etree.fromstring(text)

def serialize_xml(node):
    return etree.tostring(node, method='xml', encoding='unicode')


MODIFIER_ATTRS = {"invisible", "readonly", "required", "column_invisible", "attrs", "states"}
def xml_term_adapter(term_en):
    """
    Returns an `adapter(term)` function that will ensure the modifiers are copied
    from the base `term_en` to the translated `term` when the XML structure of
    both terms match. `term_en` and any input `term` to the adapter must be valid
    XML terms. Using the adapter only makes sense if `term_en` contains some tags
    from TRANSLATED_ELEMENTS.
    """
    orig_node = parse_xml(f"<div>{term_en}</div>")

    def same_struct_iter(left, right):
        if left.tag != right.tag or len(left) != len(right):
            raise ValueError("Non matching struct")
        yield left, right
        left_iter = left.iterchildren()
        right_iter = right.iterchildren()
        for lc, rc in zip(left_iter, right_iter):
            yield from same_struct_iter(lc, rc)

    def adapter(term):
        new_node = parse_xml(f"<div>{term}</div>")
        try:
            for orig_n, new_n in same_struct_iter(orig_node, new_node):
                removed_attrs = [k for k in new_n.attrib if k in MODIFIER_ATTRS and k not in orig_n.attrib]
                for k in removed_attrs:
                    del new_n.attrib[k]
                keep_attrs = {k: v for k, v in orig_n.attrib.items()}
                new_n.attrib.update(keep_attrs)
        except ValueError:  # non-matching structure
            return None

        # remove tags <div> and </div> from result
        return serialize_xml(new_node)[5:-6]

    return adapter


_HTML_PARSER = etree.HTMLParser(encoding='utf8')

def parse_html(text):
    try:
        parse = html.fragment_fromstring(text, parser=_HTML_PARSER)
    except (etree.ParserError, TypeError) as e:
        raise UserError(_("Error while parsing view:\n\n%s") % e) from e
    return parse

def serialize_html(node):
    return etree.tostring(node, method='html', encoding='unicode')


def xml_translate(callback, value):
    """ Translate an XML value (string), using `callback` for translating text
        appearing in `value`.
    """
    if not value:
        return value

    try:
        root = parse_xml(value)
        result = translate_xml_node(root, callback, parse_xml, serialize_xml)
        return serialize_xml(result)
    except etree.ParseError:
        # fallback for translated terms: use an HTML parser and wrap the term
        root = parse_html(u"<div>%s</div>" % value)
        result = translate_xml_node(root, callback, parse_xml, serialize_xml)
        # remove tags <div> and </div> from result
        return serialize_xml(result)[5:-6]

def xml_term_converter(value):
    """ Convert the HTML fragment ``value`` to XML if necessary
    """
    # wrap value inside a div and parse it as HTML
    div = f"<div>{value}</div>"
    root = etree.fromstring(div, etree.HTMLParser())
    # root is html > body > div
    # serialize div as XML and discard surrounding tags
    return etree.tostring(root[0][0], encoding='unicode')[5:-6]

def html_translate(callback, value):
    """ Translate an HTML value (string), using `callback` for translating text
        appearing in `value`.
    """
    if not value:
        return value

    try:
        # value may be some HTML fragment, wrap it into a div
        root = parse_html("<div>%s</div>" % value)
        result = translate_xml_node(root, callback, parse_html, serialize_html)
        # remove tags <div> and </div> from result
        value = serialize_html(result)[5:-6].replace('\xa0', '&nbsp;')
    except ValueError:
        _logger.exception("Cannot translate malformed HTML, using source value instead")

    return value

def html_term_converter(value):
    """ Convert the HTML fragment ``value`` to XML if necessary
    """
    # wrap value inside a div and parse it as HTML
    div = f"<div>{value}</div>"
    root = etree.fromstring(div, etree.HTMLParser())
    # root is html > body > div
    # serialize div as HTML and discard surrounding tags
    return etree.tostring(root[0][0], encoding='unicode', method='html')[5:-6]


def get_text_content(term):
    """ Return the textual content of the given term. """
    content = html.fromstring(term).text_content()
    return " ".join(content.split())

def is_text(term):
    """ Return whether the term has only text. """
    return len(html.fromstring(f"<_>{term}</_>")) == 0

xml_translate.get_text_content = get_text_content
html_translate.get_text_content = get_text_content

xml_translate.term_converter = xml_term_converter
html_translate.term_converter = html_term_converter

xml_translate.is_text = is_text
html_translate.is_text = is_text

xml_translate.term_adapter = xml_term_adapter

def translate_sql_constraint(cr, key, lang):
    cr.execute("""
        SELECT COALESCE(c.message->>%s, c.message->>'en_US') as message
        FROM ir_model_constraint c
        WHERE name=%s and type='u'
        """, (lang, key))
    return cr.fetchone()[0]

class GettextAlias(object):

    def _get_db(self):
        # find current DB based on thread/worker db name (see netsvc)
        db_name = getattr(threading.current_thread(), 'dbname', None)
        if db_name:
            return odoo.sql_db.db_connect(db_name)

    def _get_cr(self, frame, allow_create=True):
        # try, in order: cr, cursor, self.env.cr, self.cr,
        # request.env.cr
        if 'cr' in frame.f_locals:
            return frame.f_locals['cr'], False
        if 'cursor' in frame.f_locals:
            return frame.f_locals['cursor'], False
        s = frame.f_locals.get('self')
        if hasattr(s, 'env'):
            return s.env.cr, False
        if hasattr(s, 'cr'):
            return s.cr, False
        try:
            from odoo.http import request
            return request.env.cr, False
        except RuntimeError:
            pass
        if allow_create:
            # create a new cursor
            db = self._get_db()
            if db is not None:
                return db.cursor(), True
        return None, False

    def _get_uid(self, frame):
        # try, in order: uid, user, self.env.uid
        if 'uid' in frame.f_locals:
            return frame.f_locals['uid']
        if 'user' in frame.f_locals:
            return int(frame.f_locals['user'])      # user may be a record
        s = frame.f_locals.get('self')
        return s.env.uid

    def _get_lang(self, frame):
        # try, in order: context.get('lang'), kwargs['context'].get('lang'),
        # self.env.lang, self.localcontext.get('lang'), request.env.lang
        lang = None
        if frame.f_locals.get('context'):
            lang = frame.f_locals['context'].get('lang')
        if not lang:
            kwargs = frame.f_locals.get('kwargs', {})
            if kwargs.get('context'):
                lang = kwargs['context'].get('lang')
        if not lang:
            s = frame.f_locals.get('self')
            if hasattr(s, 'env'):
                lang = s.env.lang
            if not lang:
                if hasattr(s, 'localcontext'):
                    lang = s.localcontext.get('lang')
            if not lang:
                try:
                    from odoo.http import request
                    if request.httprequest.cookies:
                        lang = request.httprequest.cookies.get('frontend_lang')
                    if not lang:
                        lang = request.env.lang
                except RuntimeError:
                    pass
            if not lang:
                # Last resort: attempt to guess the language of the user
                # Pitfall: some operations are performed in sudo mode, and we
                #          don't know the original uid, so the language may
                #          be wrong when the admin language differs.
                (cr, dummy) = self._get_cr(frame, allow_create=False)
                uid = self._get_uid(frame)
                if cr and uid:
                    env = odoo.api.Environment(cr, uid, {})
                    lang = env['res.users'].context_get()['lang']
        return lang

    def __call__(self, source, *args, **kwargs):
        translation = self._get_translation(source)
        assert not (args and kwargs)
        if args or kwargs:
            if any(isinstance(a, Markup) for a in itertools.chain(args, kwargs.values())):
                translation = escape(translation)
            try:
                return translation % (args or kwargs)
            except (TypeError, ValueError, KeyError):
                bad = translation
                # fallback: apply to source before logging exception (in case source fails)
                translation = source % (args or kwargs)
                _logger.exception('Bad translation %r for string %r', bad, source)
        return translation

    def _get_translation(self, source, module=None):
        try:
            frame = inspect.currentframe().f_back.f_back
            lang = self._get_lang(frame)
            if lang and lang != 'en_US':
                if not module:
                    path = inspect.getfile(frame)
                    path_info = odoo.modules.get_resource_from_path(path)
                    module = path_info[0] if path_info else 'base'
                return code_translations.get_python_translations(module, lang).get(source, source)
            else:
                _logger.debug('no translation language detected, skipping translation for "%r" ', source)
        except Exception:
            _logger.debug('translation went wrong for "%r", skipped', source)
                # if so, double-check the root/base translations filenames
        return source


@functools.total_ordering
class _lt:
    """ Lazy code translation

    Similar to GettextAlias but the translation lookup will be done only at
    __str__ execution.

    A code using translated global variables such as:

    LABEL = _lt("User")

    def _compute_label(self):
        context = {'lang': self.partner_id.lang}
        self.user_label = LABEL

    works as expected (unlike the classic GettextAlias implementation).
    """

    __slots__ = ['_source', '_args', '_module']

    def __init__(self, source, *args, **kwargs):
        self._source = source
        assert not (args and kwargs)
        self._args = args or kwargs

        frame = inspect.currentframe().f_back
        path = inspect.getfile(frame)
        path_info = odoo.modules.get_resource_from_path(path)
        self._module = path_info[0] if path_info else 'base'

    def __str__(self):
        # Call _._get_translation() like _() does, so that we have the same number
        # of stack frames calling _get_translation()
        translation = _._get_translation(self._source, self._module)
        if self._args:
            try:
                return translation % self._args
            except (TypeError, ValueError, KeyError):
                bad = translation
                # fallback: apply to source before logging exception (in case source fails)
                translation = self._source % self._args
                _logger.exception('Bad translation %r for string %r', bad, self._source)
        return translation

    def __eq__(self, other):
        """ Prevent using equal operators

        Prevent direct comparisons with ``self``.
        One should compare the translation of ``self._source`` as ``str(self) == X``.
        """
        raise NotImplementedError()

    def __lt__(self, other):
        raise NotImplementedError()

    def __add__(self, other):
        # Call _._get_translation() like _() does, so that we have the same number
        # of stack frames calling _get_translation()
        if isinstance(other, str):
            return _._get_translation(self._source) + other
        elif isinstance(other, _lt):
            return _._get_translation(self._source) + _._get_translation(other._source)
        return NotImplemented

    def __radd__(self, other):
        # Call _._get_translation() like _() does, so that we have the same number
        # of stack frames calling _get_translation()
        if isinstance(other, str):
            return other + _._get_translation(self._source)
        return NotImplemented

_ = GettextAlias()


def quote(s):
    """Returns quoted PO term string, with special PO characters escaped"""
    assert r"\n" not in s, "Translation terms may not include escaped newlines ('\\n'), please use only literal newlines! (in '%s')" % s
    return '"%s"' % s.replace('\\','\\\\') \
                     .replace('"','\\"') \
                     .replace('\n', '\\n"\n"')

re_escaped_char = re.compile(r"(\\.)")
re_escaped_replacements = {'n': '\n', 't': '\t',}

def _sub_replacement(match_obj):
    return re_escaped_replacements.get(match_obj.group(1)[1], match_obj.group(1)[1])

def unquote(str):
    """Returns unquoted PO term string, with special PO characters unescaped"""
    return re_escaped_char.sub(_sub_replacement, str[1:-1])

def TranslationFileReader(source, fileformat='po'):
    """ Iterate over translation file to return Odoo translation entries """
    if fileformat == 'csv':
        return CSVFileReader(source)
    if fileformat == 'po':
        return PoFileReader(source)
    _logger.info('Bad file format: %s', fileformat)
    raise Exception(_('Bad file format: %s', fileformat))

class CSVFileReader:
    def __init__(self, source):
        _reader = codecs.getreader('utf-8')
        self.source = csv.DictReader(_reader(source), quotechar='"', delimiter=',')
        self.prev_code_src = ""

    def __iter__(self):
        for entry in self.source:

            # determine <module>.<imd_name> from res_id
            if entry["res_id"] and entry["res_id"].isnumeric():
                # res_id is an id or line number
                entry["res_id"] = int(entry["res_id"])
            elif not entry.get("imd_name"):
                # res_id is an external id and must follow <module>.<name>
                entry["module"], entry["imd_name"] = entry["res_id"].split(".")
                entry["res_id"] = None
            if entry["type"] == "model" or entry["type"] == "model_terms":
                entry["imd_model"] = entry["name"].partition(',')[0]

            if entry["type"] == "code":
                if entry["src"] == self.prev_code_src:
                    # skip entry due to unicity constrain on code translations
                    continue
                self.prev_code_src = entry["src"]

            yield entry

class PoFileReader:
    """ Iterate over po file to return Odoo translation entries """
    def __init__(self, source):

        def get_pot_path(source_name):
            # when fileobj is a TemporaryFile, its name is an inter in P3, a string in P2
            if isinstance(source_name, str) and source_name.endswith('.po'):
                # Normally the path looks like /path/to/xxx/i18n/lang.po
                # and we try to find the corresponding
                # /path/to/xxx/i18n/xxx.pot file.
                # (Sometimes we have 'i18n_extra' instead of just 'i18n')
                path = Path(source_name)
                filename = path.parent.parent.name + '.pot'
                pot_path = path.with_name(filename)
                return pot_path.exists() and str(pot_path) or False
            return False

        # polib accepts a path or the file content as a string, not a fileobj
        if isinstance(source, str):
            self.pofile = polib.pofile(source)
            pot_path = get_pot_path(source)
        else:
            # either a BufferedIOBase or result from NamedTemporaryFile
            self.pofile = polib.pofile(source.read().decode())
            pot_path = get_pot_path(source.name)

        if pot_path:
            # Make a reader for the POT file
            # (Because the POT comments are correct on GitHub but the
            # PO comments tends to be outdated. See LP bug 933496.)
            self.pofile.merge(polib.pofile(pot_path))

    def __iter__(self):
        for entry in self.pofile:
            if entry.obsolete:
                continue

            # in case of moduleS keep only the first
            match = re.match(r"(module[s]?): (\w+)", entry.comment)
            _, module = match.groups()
            comments = "\n".join([c for c in entry.comment.split('\n') if not c.startswith('module:')])
            source = entry.msgid
            translation = entry.msgstr
            found_code_occurrence = False
            for occurrence, line_number in entry.occurrences:
                match = re.match(r'(model|model_terms):([\w.]+),([\w]+):(\w+)\.([^ ]+)', occurrence)
                if match:
                    type, model_name, field_name, module, xmlid = match.groups()
                    yield {
                        'type': type,
                        'imd_model': model_name,
                        'name': model_name+','+field_name,
                        'imd_name': xmlid,
                        'res_id': None,
                        'src': source,
                        'value': translation,
                        'comments': comments,
                        'module': module,
                    }
                    continue

                match = re.match(r'(code):([\w/.]+)', occurrence)
                if match:
                    type, name = match.groups()
                    if found_code_occurrence:
                        # unicity constrain on code translation
                        continue
                    found_code_occurrence = True
                    yield {
                        'type': type,
                        'name': name,
                        'src': source,
                        'value': translation,
                        'comments': comments,
                        'res_id': int(line_number),
                        'module': module,
                    }
                    continue

                match = re.match(r'(selection):([\w.]+),([\w]+)', occurrence)
                if match:
                    _logger.info("Skipped deprecated occurrence %s", occurrence)
                    continue

                match = re.match(r'(sql_constraint|constraint):([\w.]+)', occurrence)
                if match:
                    _logger.info("Skipped deprecated occurrence %s", occurrence)
                    continue
                _logger.error("malformed po file: unknown occurrence: %s", occurrence)

def TranslationFileWriter(target, fileformat='po', lang=None):
    """ Iterate over translation file to return Odoo translation entries """
    if fileformat == 'csv':
        return CSVFileWriter(target)

    if fileformat == 'po':
        return PoFileWriter(target, lang=lang)

    if fileformat == 'tgz':
        return TarFileWriter(target, lang=lang)

    raise Exception(_('Unrecognized extension: must be one of '
                      '.csv, .po, or .tgz (received .%s).') % fileformat)


class CSVFileWriter:
    def __init__(self, target):
        self.writer = pycompat.csv_writer(target, dialect='UNIX')
        # write header first
        self.writer.writerow(("module","type","name","res_id","src","value","comments"))


    def write_rows(self, rows):
        for module, type, name, res_id, src, trad, comments in rows:
            comments = '\n'.join(comments)
            self.writer.writerow((module, type, name, res_id, src, trad, comments))


class PoFileWriter:
    """ Iterate over po file to return Odoo translation entries """
    def __init__(self, target, lang):

        self.buffer = target
        self.lang = lang
        self.po = polib.POFile()

    def write_rows(self, rows):
        # we now group the translations by source. That means one translation per source.
        grouped_rows = {}
        modules = set()
        for module, type, name, res_id, src, trad, comments in rows:
            row = grouped_rows.setdefault(src, {})
            row.setdefault('modules', set()).add(module)
            if not row.get('translation') and trad != src:
                row['translation'] = trad
            row.setdefault('tnrs', []).append((type, name, res_id))
            row.setdefault('comments', set()).update(comments)
            modules.add(module)

        for src, row in sorted(grouped_rows.items()):
            if not self.lang:
                # translation template, so no translation value
                row['translation'] = ''
            elif not row.get('translation'):
                row['translation'] = ''
            self.add_entry(sorted(row['modules']), sorted(row['tnrs']), src, row['translation'], sorted(row['comments']))

        import odoo.release as release
        self.po.header = "Translation of %s.\n" \
                    "This file contains the translation of the following modules:\n" \
                    "%s" % (release.description, ''.join("\t* %s\n" % m for m in modules))
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M+0000')
        self.po.metadata = {
            'Project-Id-Version': "%s %s" % (release.description, release.version),
            'Report-Msgid-Bugs-To': '',
            'POT-Creation-Date': now,
            'PO-Revision-Date': now,
            'Last-Translator': '',
            'Language-Team': '',
            'MIME-Version': '1.0',
            'Content-Type': 'text/plain; charset=UTF-8',
            'Content-Transfer-Encoding': '',
            'Plural-Forms': '',
        }

        # buffer expects bytes
        self.buffer.write(str(self.po).encode())

    def add_entry(self, modules, tnrs, source, trad, comments=None):
        entry = polib.POEntry(
            msgid=source,
            msgstr=trad,
        )
        plural = len(modules) > 1 and 's' or ''
        entry.comment = "module%s: %s" % (plural, ', '.join(modules))
        if comments:
            entry.comment += "\n" + "\n".join(comments)

        code = False
        for typy, name, res_id in tnrs:
            if typy == 'code':
                code = True
                res_id = 0
            if isinstance(res_id, int) or res_id.isdigit():
                # second term of occurrence must be a digit
                # occurrence line at 0 are discarded when rendered to string
                entry.occurrences.append((u"%s:%s" % (typy, name), str(res_id)))
            else:
                entry.occurrences.append((u"%s:%s:%s" % (typy, name, res_id), ''))
        if code:
            # TODO 17.0: remove the flag python-format in all PO/POT files
            # The flag is used in a wrong way. It marks all code translations even for javascript translations.
            entry.flags.append("python-format")
        self.po.append(entry)


class TarFileWriter:

    def __init__(self, target, lang):
        self.tar = tarfile.open(fileobj=target, mode='w|gz')
        self.lang = lang

    def write_rows(self, rows):
        rows_by_module = defaultdict(list)
        for row in rows:
            module = row[0]
            rows_by_module[module].append(row)

        for mod, modrows in rows_by_module.items():
            with io.BytesIO() as buf:
                po = PoFileWriter(buf, lang=self.lang)
                po.write_rows(modrows)
                buf.seek(0)

                info = tarfile.TarInfo(
                    join(mod, 'i18n', '{basename}.{ext}'.format(
                        basename=self.lang or mod,
                        ext='po' if self.lang else 'pot',
                    )))
                # addfile will read <size> bytes from the buffer so
                # size *must* be set first
                info.size = len(buf.getvalue())

                self.tar.addfile(info, fileobj=buf)

        self.tar.close()

# Methods to export the translation file
def trans_export(lang, modules, buffer, format, cr):
    reader = TranslationModuleReader(cr, modules=modules, lang=lang)
    writer = TranslationFileWriter(buffer, fileformat=format, lang=lang)
    writer.write_rows(reader)

# pylint: disable=redefined-builtin
def trans_export_records(lang, model_name, ids, buffer, format, cr):
    reader = TranslationRecordReader(cr, model_name, ids, lang=lang)
    writer = TranslationFileWriter(buffer, fileformat=format, lang=lang)
    writer.write_rows(reader)


def _push(callback, term, source_line):
    """ Sanity check before pushing translation terms """
    term = (term or "").strip()
    # Avoid non-char tokens like ':' '...' '.00' etc.
    if len(term) > 8 or any(x.isalpha() for x in term):
        callback(term, source_line)

def _extract_translatable_qweb_terms(element, callback):
    """ Helper method to walk an etree document representing
        a QWeb template, and call ``callback(term)`` for each
        translatable term that is found in the document.

        :param etree._Element element: root of etree document to extract terms from
        :param Callable callback: a callable in the form ``f(term, source_line)``,
                                  that will be called for each extracted term.
    """
    # not using elementTree.iterparse because we need to skip sub-trees in case
    # the ancestor element had a reason to be skipped
    for el in element:
        if isinstance(el, SKIPPED_ELEMENT_TYPES): continue
        if (el.tag.lower() not in SKIPPED_ELEMENTS
                and "t-js" not in el.attrib
                and not ("t-jquery" in el.attrib and "t-operation" not in el.attrib)
                and not (el.tag == 'attribute' and el.get('name') not in TRANSLATED_ATTRS)
                and el.get("t-translation", '').strip() != "off"):

            _push(callback, el.text, el.sourceline)
            # heuristic: tags with names starting with an uppercase letter are
            # component nodes
            is_component = el.tag[0].isupper() or "t-component" in el.attrib or "t-set-slot" in el.attrib
            for attr in el.attrib:
                if (not is_component and attr in OWL_TRANSLATED_ATTRS) or (is_component and attr.endswith(".translate")):
                    _push(callback, el.attrib[attr], el.sourceline)
            _extract_translatable_qweb_terms(el, callback)
        _push(callback, el.tail, el.sourceline)


def babel_extract_qweb(fileobj, keywords, comment_tags, options):
    """Babel message extractor for qweb template files.

    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    :rtype: Iterable
    """
    result = []
    def handle_text(text, lineno):
        result.append((lineno, None, text, []))
    tree = etree.parse(fileobj)
    _extract_translatable_qweb_terms(tree.getroot(), handle_text)
    return result


def extract_formula_terms(formula):
    """Extract strings in a spreadsheet formula which are arguments to '_t' functions

        >>> extract_formula_terms('=_t("Hello") + _t("Raoul")')
        ["Hello", "Raoul"]
    """
    tokens = generate_tokens(io.StringIO(formula).readline)
    tokens = (token for token in tokens if token.type not in {NEWLINE, INDENT, DEDENT})
    for t1 in tokens:
        if not t1.string == '_t':
            continue
        t2 = next(tokens, None)
        if t2 and t2.string == '(':
            t3 = next(tokens, None)
            t4 = next(tokens, None)
            if t4 and t4.string == ')' and t3 and t3.type == STRING:
                yield t3.string[1:][:-1] # strip leading and trailing quotes


def extract_spreadsheet_terms(fileobj, keywords, comment_tags, options):
    """Babel message extractor for spreadsheet data files.

    :param fileobj: the file-like object the messages should be extracted from
    :param keywords: a list of keywords (i.e. function names) that should
                     be recognized as translation functions
    :param comment_tags: a list of translator tags to search for and
                         include in the results
    :param options: a dictionary of additional options (optional)
    :return: an iterator over ``(lineno, funcname, message, comments)``
             tuples
    """
    terms = set()
    data = json.load(fileobj)
    for sheet in data.get('sheets', []):
        for cell in sheet['cells'].values():
            content = cell.get('content', '')
            if content.startswith('='):
                terms.update(extract_formula_terms(content))
            else:
                markdown_link = re.fullmatch(r'\[(.+)\]\(.+\)', content)
                if markdown_link:
                    terms.add(markdown_link[1])
        for figure in sheet['figures']:
            terms.add(figure['data']['title'])
            if 'baselineDescr' in figure['data']:
                terms.add(figure['data']['baselineDescr'])
    pivots = data.get('pivots', {}).values()
    lists = data.get('lists', {}).values()
    for data_source in itertools.chain(lists, pivots):
        if 'name' in data_source:
            terms.add(data_source['name'])
    for global_filter in data.get('globalFilters', []):
        terms.add(global_filter['label'])
    return (
        (0, None, term, [])
        for term in terms
        if any(x.isalpha() for x in term)
    )

ImdInfo = namedtuple('ExternalId', ['name', 'model', 'res_id', 'module'])


class TranslationReader:
    def __init__(self, cr, lang=None):
        self._cr = cr
        self._lang = lang or 'en_US'
        self.env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        self._to_translate = []

    def __iter__(self):
        for module, source, name, res_id, ttype, comments, _record_id, value in self._to_translate:
            yield (module, ttype, name, res_id, source, encode(odoo.tools.ustr(value)), comments)

    def _push_translation(self, module, ttype, name, res_id, source, comments=None, record_id=None, value=None):
        """ Insert a translation that will be used in the file generation
        In po file will create an entry
        #: <ttype>:<name>:<res_id>
        #, <comment>
        msgid "<source>"
        record_id is the database id of the record being translated
        """
        # empty and one-letter terms are ignored, they probably are not meant to be
        # translated, and would be very hard to translate anyway.
        sanitized_term = (source or '').strip()
        # remove non-alphanumeric chars
        sanitized_term = re.sub(r'\W+', '', sanitized_term)
        if not sanitized_term or len(sanitized_term) <= 1:
            return
        self._to_translate.append((module, source, name, res_id, ttype, tuple(comments or ()), record_id, value))

    def _export_imdinfo(self, model: str, imd_per_id: dict[int, ImdInfo]):
        records = self._get_translatable_records(imd_per_id.values())
        if not records:
            return

        env = records.env
        for record in records.with_context(check_translations=True):
            module = imd_per_id[record.id].module
            xml_name = "%s.%s" % (module, imd_per_id[record.id].name)
            for field_name, field in record._fields.items():
                # ir_actions_actions.name is filtered because unlike other inherited fields,
                # this field is inherited as postgresql inherited columns.
                # From our business perspective, the parent column is no need to be translated,
                # but it is need to be set to jsonb column, since the child columns need to be translated
                # And export the parent field may make one value to be translated twice in transifex
                #
                # Some ir_model_fields.field_description are filtered
                # because their fields have falsy attribute export_string_translation
                if (
                        not (field.translate and field.store)
                        or str(field) == 'ir.actions.actions.name'
                        or (str(field) == 'ir.model.fields.field_description'
                            and not env[record.model]._fields[record.name].export_string_translation)
                ):
                    continue
                name = model + "," + field_name
                value_en = record[field_name] or ''
                value_lang = record.with_context(lang=self._lang)[field_name] or ''
                trans_type = 'model_terms' if callable(field.translate) else 'model'
                try:
                    translation_dictionary = field.get_translation_dictionary(value_en, {self._lang: value_lang})
                except Exception:
                    _logger.exception("Failed to extract terms from %s %s", xml_name, name)
                    continue
                for term_en, term_langs in translation_dictionary.items():
                    term_lang = term_langs.get(self._lang)
                    self._push_translation(module, trans_type, name, xml_name, term_en, record_id=record.id, value=term_lang if term_lang != term_en else '')

    def _get_translatable_records(self, imd_records):
        """ Filter the records that are translatable

        A record is considered as untranslatable if:
        - it does not exist
        - the model is flagged with _translate=False
        - it is a field of a model flagged with _translate=False
        - it is a selection of a field of a model flagged with _translate=False

        :param records: a list of namedtuple ImdInfo belonging to the same model
        """
        model = next(iter(imd_records)).model
        if model not in self.env:
            _logger.error("Unable to find object %r", model)
            return self.env["_unknown"].browse()

        if not self.env[model]._translate:
            return self.env[model].browse()

        res_ids = [r.res_id for r in imd_records]
        records = self.env[model].browse(res_ids).exists()
        if len(records) < len(res_ids):
            missing_ids = set(res_ids) - set(records.ids)
            missing_records = [f"{r.module}.{r.name}" for r in imd_records if r.res_id in missing_ids]
            _logger.warning("Unable to find records of type %r with external ids %s", model, ', '.join(missing_records))
            if not records:
                return records

        if model == 'ir.model.fields.selection':
            fields = defaultdict(list)
            for selection in records:
                fields[selection.field_id] = selection
            for field, selection in fields.items():
                field_name = field.name
                field_model = self.env.get(field.model)
                if (field_model is None or not field_model._translate or
                        field_name not in field_model._fields):
                    # the selection is linked to a model with _translate=False, remove it
                    records -= selection
        elif model == 'ir.model.fields':
            for field in records:
                field_name = field.name
                field_model = self.env.get(field.model)
                if (field_model is None or not field_model._translate or
                        field_name not in field_model._fields):
                    # the field is linked to a model with _translate=False, remove it
                    records -= field

        return records


class TranslationRecordReader(TranslationReader):
    """ Retrieve translations for specified records, the reader will
    1. create external ids for records without external ids
    2. export translations for stored translated and inherited translated fields
    :param cr: cursor to database to export
    :param model_name: model_name for the records to export
    :param ids: ids of the records to export
    :param field_names: field names to export, if not set, export all translatable fields
    :param lang: language code to retrieve the translations retrieve source terms only if not set
    """
    def __init__(self, cr, model_name, ids, field_names=None, lang=None):
        super().__init__(cr, lang)
        self._records = self.env[model_name].browse(ids)
        self._field_names = field_names or list(self._records._fields.keys())

        self._export_translatable_records(self._records, self._field_names)

    def _export_translatable_records(self, records, field_names):
        """ Export translations of all stored/inherited translated fields. Create external id if needed. """
        if not records:
            return

        fields = records._fields

        if records._inherits:
            inherited_fields = defaultdict(list)
            for field_name in field_names:
                field = records._fields[field_name]
                if field.translate and not field.store and field.inherited_field:
                    inherited_fields[field.inherited_field.model_name].append(field_name)
            for parent_mname, parent_fname in records._inherits.items():
                if parent_mname in inherited_fields:
                    self._export_translatable_records(records[parent_fname], inherited_fields[parent_mname])

        if not any(fields[field_name].translate and fields[field_name].store for field_name in field_names):
            return

        records._BaseModel__ensure_xml_id()

        model_name = records._name
        query = """SELECT min(concat(module, '.', name)), res_id
                             FROM ir_model_data
                            WHERE model = %s
                              AND res_id = ANY(%s)
                         GROUP BY model, res_id"""

        self._cr.execute(query, (model_name, records.ids))

        imd_per_id = {
            res_id: ImdInfo((tmp := module_xml_name.split('.', 1))[1], model_name, res_id, tmp[0])
            for module_xml_name, res_id in self._cr.fetchall()
        }

        self._export_imdinfo(model_name, imd_per_id)


class TranslationModuleReader(TranslationReader):
    """ Retrieve translated records per module

    :param cr: cursor to database to export
    :param modules: list of modules to filter the exported terms, can be ['all']
                    records with no external id are always ignored
    :param lang: language code to retrieve the translations
                 retrieve source terms only if not set
    """

    def __init__(self, cr, modules=None, lang=None):
        super().__init__(cr, lang)
        self._modules = modules or ['all']
        self._path_list = [(path, True) for path in odoo.addons.__path__]
        self._installed_modules = [
            m['name']
            for m in self.env['ir.module.module'].search_read([('state', '=', 'installed')], fields=['name'])
        ]

        self._export_translatable_records()
        self._export_translatable_resources()

    def _export_translatable_records(self):
        """ Export translations of all translated records having an external id """

        query = """SELECT min(name), model, res_id, module
                     FROM ir_model_data
                    WHERE module = ANY(%s)
                 GROUP BY model, res_id, module
                 ORDER BY module, model, min(name)"""

        if 'all' not in self._modules:
            query_param = list(self._modules)
        else:
            query_param = self._installed_modules

        self._cr.execute(query, (query_param,))

        records_per_model = defaultdict(dict)
        for (xml_name, model, res_id, module) in self._cr.fetchall():
            records_per_model[model][res_id] = ImdInfo(xml_name, model, res_id, module)

        for model, imd_per_id in records_per_model.items():
            self._export_imdinfo(model, imd_per_id)

    def _get_module_from_path(self, path):
        for (mp, rec) in self._path_list:
            mp = os.path.join(mp, '')
            dirname = os.path.join(os.path.dirname(path), '')
            if rec and path.startswith(mp) and dirname != mp:
                path = path[len(mp):]
                return path.split(os.path.sep)[0]
        return 'base' # files that are not in a module are considered as being in 'base' module

    def _verified_module_filepaths(self, fname, path, root):
        fabsolutepath = join(root, fname)
        frelativepath = fabsolutepath[len(path):]
        display_path = "addons%s" % frelativepath
        module = self._get_module_from_path(fabsolutepath)
        if ('all' in self._modules or module in self._modules) and module in self._installed_modules:
            if os.path.sep != '/':
                display_path = display_path.replace(os.path.sep, '/')
            return module, fabsolutepath, frelativepath, display_path
        return None, None, None, None

    def _babel_extract_terms(self, fname, path, root, extract_method="python", trans_type='code',
                               extra_comments=None, extract_keywords={'_': None}):

        module, fabsolutepath, _, display_path = self._verified_module_filepaths(fname, path, root)
        if not module:
            return
        extra_comments = extra_comments or []
        src_file = file_open(fabsolutepath, 'rb')
        options = {}
        if extract_method == 'python':
            options['encoding'] = 'UTF-8'
            translations = code_translations.get_python_translations(module, self._lang)
        else:
            translations = code_translations.get_web_translations(module, self._lang)
            translations = {tran['id']: tran['string'] for tran in translations['messages']}
        try:
            for extracted in extract.extract(extract_method, src_file, keywords=extract_keywords, options=options):
                # Babel 0.9.6 yields lineno, message, comments
                # Babel 1.3 yields lineno, message, comments, context
                lineno, message, comments = extracted[:3]
                value = translations.get(message, '')
                self._push_translation(module, trans_type, display_path, lineno,
                                 encode(message), comments + extra_comments, value=value)
        except Exception:
            _logger.exception("Failed to extract terms from %s", fabsolutepath)
        finally:
            src_file.close()

    def _export_translatable_resources(self):
        """ Export translations for static terms

        This will include:
        - the python strings marked with _() or _lt()
        - the javascript strings marked with _t() or _lt() inside static/src/js/
        - the strings inside Qweb files inside static/src/xml/
        - the spreadsheet data files
        """

        # Also scan these non-addon paths
        for bin_path in ['osv', 'report', 'modules', 'service', 'tools']:
            self._path_list.append((os.path.join(config['root_path'], bin_path), True))
        # non-recursive scan for individual files in root directory but without
        # scanning subdirectories that may contain addons
        self._path_list.append((config['root_path'], False))
        _logger.debug("Scanning modules at paths: %s", self._path_list)

        spreadsheet_files_regex = re.compile(r".*_dashboard(\.osheet)?\.json$")

        for (path, recursive) in self._path_list:
            _logger.debug("Scanning files of modules at %s", path)
            for root, dummy, files in os.walk(path, followlinks=True):
                for fname in fnmatch.filter(files, '*.py'):
                    self._babel_extract_terms(fname, path, root, 'python',
                                              extra_comments=[PYTHON_TRANSLATION_COMMENT],
                                              extract_keywords={'_': None, '_lt': None})
                if fnmatch.fnmatch(root, '*/static/src*'):
                    # Javascript source files
                    for fname in fnmatch.filter(files, '*.js'):
                        self._babel_extract_terms(fname, path, root, 'javascript',
                                                  extra_comments=[JAVASCRIPT_TRANSLATION_COMMENT],
                                                  extract_keywords={'_t': None, '_lt': None})
                    # QWeb template files
                    for fname in fnmatch.filter(files, '*.xml'):
                        self._babel_extract_terms(fname, path, root, 'odoo.tools.translate:babel_extract_qweb',
                                                  extra_comments=[JAVASCRIPT_TRANSLATION_COMMENT])
                if fnmatch.fnmatch(root, '*/data/*'):
                    for fname in filter(spreadsheet_files_regex.match, files):
                        self._babel_extract_terms(fname, path, root, 'odoo.tools.translate:extract_spreadsheet_terms',
                                                  extra_comments=[JAVASCRIPT_TRANSLATION_COMMENT])
                if not recursive:
                    # due to topdown, first iteration is in first level
                    break


def DeepDefaultDict():
    return defaultdict(DeepDefaultDict)


class TranslationImporter:
    """ Helper object for importing translation files to a database.
    This class provides a convenient API to load the translations from many
    files and import them all at once, which helps speeding up the whole import.
    """

    def __init__(self, cr, verbose=True):
        self.cr = cr
        self.verbose = verbose
        self.env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

        # {model_name: {field_name: {xmlid: {lang: value}}}}
        self.model_translations = DeepDefaultDict()
        # {model_name: {field_name: {xmlid: {src: {lang: value}}}}}
        self.model_terms_translations = DeepDefaultDict()

    def load_file(self, filepath, lang, xmlids=None):
        """ Load translations from the given file path.

        :param filepath: file path to open
        :param lang: language code of the translations contained in the file;
                     the language must be present and activated in the database
        :param xmlids: if given, only translations for records with xmlid in xmlids will be loaded
        """
        with suppress(FileNotFoundError), file_open(filepath, mode='rb', env=self.env) as fileobj:
            _logger.info('loading base translation file %s for language %s', filepath, lang)
            fileformat = os.path.splitext(filepath)[-1][1:].lower()
            self.load(fileobj, fileformat, lang, xmlids=xmlids)

    def load(self, fileobj, fileformat, lang, xmlids=None):
        """Load translations from the given file object.

        :param fileobj: buffer open to a translation file
        :param fileformat: format of the `fielobj` file, one of 'po' or 'csv'
        :param lang: language code of the translations contained in `fileobj`;
                     the language must be present and activated in the database
        :param xmlids: if given, only translations for records with xmlid in xmlids will be loaded
        """
        if self.verbose:
            _logger.info('loading translation file for language %s', lang)
        if not self.env['res.lang']._lang_get(lang):
            _logger.error("Couldn't read translation for lang '%s', language not found", lang)
            return None
        try:
            fileobj.seek(0)
            reader = TranslationFileReader(fileobj, fileformat=fileformat)
            self._load(reader, lang, xmlids)
        except IOError:
            iso_lang = get_iso_codes(lang)
            filename = '[lang: %s][format: %s]' % (iso_lang or 'new', fileformat)
            _logger.exception("couldn't read translation file %s", filename)

    def _load(self, reader, lang, xmlids=None):
        if xmlids and not isinstance(xmlids, set):
            xmlids = set(xmlids)
        for row in reader:
            if not row.get('value') or not row.get('src'):  # ignore empty translations
                continue
            if row.get('type') == 'code':  # ignore code translations
                continue
            model_name = row.get('imd_model')
            module_name = row['module']
            if model_name not in self.env:
                continue
            field_name = row['name'].split(',')[1]
            field = self.env[model_name]._fields.get(field_name)
            if not field or not field.translate or not field.store:
                continue
            xmlid = module_name + '.' + row['imd_name']
            if xmlids and xmlid not in xmlids:
                continue
            if row.get('type') == 'model' and field.translate is True:
                self.model_translations[model_name][field_name][xmlid][lang] = row['value']
            elif row.get('type') == 'model_terms' and callable(field.translate):
                self.model_terms_translations[model_name][field_name][xmlid][row['src']][lang] = row['value']

    def save(self, overwrite=False, force_overwrite=False):
        """ Save translations to the database.

        For a record with 'noupdate' in ``ir_model_data``, its existing translations
        will be overwritten if ``force_overwrite or (not noupdate and overwrite)``.

        An existing translation means:
        * model translation: the ``jsonb`` value in database has the language code as key;
        * model terms translation: the term value in the language is different from the term value in ``en_US``.
        """
        if not self.model_translations and not self.model_terms_translations:
            return

        cr = self.cr
        env = self.env
        env.flush_all()

        for model_name, model_dictionary in self.model_terms_translations.items():
            Model = env[model_name]
            model_table = Model._table
            fields = Model._fields
            # field_name, {xmlid: {src: {lang: value}}}
            for field_name, field_dictionary in model_dictionary.items():
                field = fields.get(field_name)
                for sub_xmlids in cr.split_for_in_conditions(field_dictionary.keys()):
                    # [module_name, imd_name, module_name, imd_name, ...]
                    params = []
                    for xmlid in sub_xmlids:
                        params.extend(xmlid.split('.', maxsplit=1))
                    cr.execute(f'''
                        SELECT m.id, imd.module || '.' || imd.name, m."{field_name}", imd.noupdate
                        FROM "{model_table}" m, "ir_model_data" imd
                        WHERE m.id = imd.res_id
                        AND ({" OR ".join(["(imd.module = %s AND imd.name = %s)"] * (len(params) // 2))})
                    ''', params)

                    # [id, translations, id, translations, ...]
                    params = []
                    for id_, xmlid, values, noupdate in cr.fetchall():
                        if not values:
                            continue
                        _value_en = values.get('_en_US', values['en_US'])
                        if not _value_en:
                            continue

                        # {src: {lang: value}}
                        record_dictionary = field_dictionary[xmlid]
                        langs = {lang for translations in record_dictionary.values() for lang in translations.keys()}
                        translation_dictionary = field.get_translation_dictionary(
                            _value_en,
                            {
                                k: values.get(f'_{k}', v)
                                for k, v in values.items()
                                if k in langs
                            }
                        )

                        if force_overwrite or (not noupdate and overwrite):
                            # overwrite existing translations
                            for term_en, translations in record_dictionary.items():
                                translation_dictionary[term_en].update(translations)
                        else:
                            # keep existing translations
                            for term_en, translations in record_dictionary.items():
                                translations.update({k: v for k, v in translation_dictionary[term_en].items() if v != term_en})
                                translation_dictionary[term_en] = translations

                        for lang in langs:
                            # translate and confirm model_terms translations
                            values[lang] = field.translate(lambda term: translation_dictionary.get(term, {}).get(lang), _value_en)
                            values.pop(f'_{lang}', None)
                        params.extend((id_, Json(values)))
                    if params:
                        env.cr.execute(f"""
                            UPDATE "{model_table}" AS m
                            SET "{field_name}" =  t.value
                            FROM (
                                VALUES {', '.join(['(%s, %s::jsonb)'] * (len(params) // 2))}
                            ) AS t(id, value)
                            WHERE m.id = t.id
                        """, params)

        self.model_terms_translations.clear()

        for model_name, model_dictionary in self.model_translations.items():
            Model = env[model_name]
            model_table = Model._table
            for field_name, field_dictionary in model_dictionary.items():
                for sub_field_dictionary in cr.split_for_in_conditions(field_dictionary.items()):
                    # [xmlid, translations, xmlid, translations, ...]
                    params = []
                    for xmlid, translations in sub_field_dictionary:
                        params.extend([*xmlid.split('.', maxsplit=1), Json(translations)])
                    if not force_overwrite:
                        value_query = f"""CASE WHEN {overwrite} IS TRUE AND imd.noupdate IS FALSE
                        THEN m."{field_name}" || t.value
                        ELSE t.value || m."{field_name}"END"""
                    else:
                        value_query = f'm."{field_name}" || t.value'
                    env.cr.execute(f"""
                        UPDATE "{model_table}" AS m
                        SET "{field_name}" = {value_query}
                        FROM (
                            VALUES {', '.join(['(%s, %s, %s::jsonb)'] * (len(params) // 3))}
                        ) AS t(imd_module, imd_name, value)
                        JOIN "ir_model_data" AS imd
                        ON imd."model" = '{model_name}' AND imd.name = t.imd_name AND imd.module = t.imd_module
                        WHERE imd."res_id" = m."id"
                    """, params)

        self.model_translations.clear()

        env.invalidate_all()
        env.registry.clear_cache()
        if self.verbose:
            _logger.info("translations are loaded successfully")


def trans_load(cr, filepath, lang, verbose=True, overwrite=False):
    warnings.warn('The function trans_load is deprecated in favor of TranslationImporter', DeprecationWarning)
    translation_importer = TranslationImporter(cr, verbose=verbose)
    translation_importer.load_file(filepath, lang)
    translation_importer.save(overwrite=overwrite)


def trans_load_data(cr, fileobj, fileformat, lang, verbose=True, overwrite=False):
    warnings.warn('The function trans_load_data is deprecated in favor of TranslationImporter', DeprecationWarning)
    translation_importer = TranslationImporter(cr, verbose=verbose)
    translation_importer.load(fileobj, fileformat, lang)
    translation_importer.save(overwrite=overwrite)


def get_locales(lang=None):
    if lang is None:
        lang = locale.getlocale()[0]

    if os.name == 'nt':
        lang = _LOCALE2WIN32.get(lang, lang)

    def process(enc):
        ln = locale._build_localename((lang, enc))
        yield ln
        nln = locale.normalize(ln)
        if nln != ln:
            yield nln

    for x in process('utf8'): yield x

    prefenc = locale.getpreferredencoding()
    if prefenc:
        for x in process(prefenc): yield x

        prefenc = {
            'latin1': 'latin9',
            'iso-8859-1': 'iso8859-15',
            'cp1252': '1252',
        }.get(prefenc.lower())
        if prefenc:
            for x in process(prefenc): yield x

    yield lang


def resetlocale():
    # locale.resetlocale is bugged with some locales.
    for ln in get_locales():
        try:
            return locale.setlocale(locale.LC_ALL, ln)
        except locale.Error:
            continue


def load_language(cr, lang):
    """ Loads a translation terms for a language.

    Used mainly to automate language loading at db initialization.

    :param cr:
    :param str lang: language ISO code with optional underscore (``_``) and
        l10n flavor (ex: 'fr', 'fr_BE', but not 'fr-BE')
    """
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    lang_ids = env['res.lang'].with_context(active_test=False).search([('code', '=', lang)]).ids
    installer = env['base.language.install'].create({'lang_ids': [(6, 0, lang_ids)]})
    installer.lang_install()


def get_po_paths(module_name: str, lang: str):
    return get_po_paths_env(module_name, lang)


def get_po_paths_env(module_name: str, lang: str, env: odoo.api.Environment | None = None):
    lang_base = lang.split('_', 1)[0]
    # Load the base as a fallback in case a translation is missing:
    po_names = [lang_base, lang]
    # Exception for Spanish locales: they have two bases, es and es_419:
    if lang_base == 'es' and lang not in ('es_ES', 'es_419'):
        po_names.insert(1, 'es_419')
    po_paths = (
        join(module_name, dir_, filename + '.po')
        for filename in po_names
        for dir_ in ('i18n', 'i18n_extra')
    )
    for path in po_paths:
        with suppress(FileNotFoundError):
            yield file_path(path, env=env)


class CodeTranslations:
    def __init__(self):
        # {(module_name, lang): {src: value}}
        self.python_translations = {}
        # {(module_name, lang): {'message': [{'id': src, 'string': value}]}
        self.web_translations = {}

    @staticmethod
    def _read_code_translations_file(fileobj, filter_func):
        """ read and return code translations from fileobj with filter filter_func

        :param func filter_func: a filter function to drop unnecessary code translations
        """
        # current, we assume the fileobj is from the source code, which only contains the translation for the current module
        # don't use it in the import logic
        translations = {}
        fileobj.seek(0)
        reader = TranslationFileReader(fileobj, fileformat='po')
        for row in reader:
            if row.get('type') == 'code' and row.get('src') and filter_func(row):
                translations[row['src']] = row['value']
        return translations

    @staticmethod
    def _get_code_translations(module_name, lang, filter_func):
        po_paths = get_po_paths(module_name, lang)
        translations = {}
        for po_path in po_paths:
            try:
                with file_open(po_path, mode='rb') as fileobj:
                    p = CodeTranslations._read_code_translations_file(fileobj, filter_func)
                translations.update(p)
            except IOError:
                iso_lang = get_iso_codes(lang)
                filename = '[lang: %s][format: %s]' % (iso_lang or 'new', 'po')
                _logger.exception("couldn't read translation file %s", filename)
        return translations

    def _load_python_translations(self, module_name, lang):
        def filter_func(row):
            # In the pot files with new translations, a code translation should have either
            # PYTHON_TRANSLATION_COMMENT or JAVASCRIPT_TRANSLATION_COMMENT for comments.
            # If a comment has neither the above comments, the pot file uses the deprecated
            # comments. And all code translations are stored as python translations.
            return row.get('value') and (
                    PYTHON_TRANSLATION_COMMENT in row['comments']
                    or JAVASCRIPT_TRANSLATION_COMMENT not in row['comments'])
        translations = CodeTranslations._get_code_translations(module_name, lang, filter_func)
        self.python_translations[(module_name, lang)] = translations

    def _load_web_translations(self, module_name, lang):
        def filter_func(row):
            return row.get('value') and (
                    JAVASCRIPT_TRANSLATION_COMMENT in row['comments']
                    or WEB_TRANSLATION_COMMENT in row['comments'])
        translations = CodeTranslations._get_code_translations(module_name, lang, filter_func)
        self.web_translations[(module_name, lang)] = {
            "messages": [{"id": src, "string": value} for src, value in translations.items()]
        }

    def get_python_translations(self, module_name, lang):
        if (module_name, lang) not in self.python_translations:
            self._load_python_translations(module_name, lang)
        return self.python_translations[(module_name, lang)]

    def get_web_translations(self, module_name, lang):
        if (module_name, lang) not in self.web_translations:
            self._load_web_translations(module_name, lang)
        return self.web_translations[(module_name, lang)]


code_translations = CodeTranslations()


def _get_translation_upgrade_queries(cr, field):
    """ Return a pair of lists ``migrate_queries, cleanup_queries`` of SQL queries. The queries in
    ``migrate_queries`` do migrate the data from table ``_ir_translation`` to the corresponding
    field's column, while the queries in ``cleanup_queries`` remove the corresponding data from
    table ``_ir_translation``.
    """
    Model = odoo.registry(cr.dbname)[field.model_name]
    translation_name = f"{field.model_name},{field.name}"
    migrate_queries = []
    cleanup_queries = []

    if field.translate is True:
        emtpy_src = """'{"en_US": ""}'::jsonb"""
        query = f"""
            WITH t AS (
                SELECT it.res_id as res_id, jsonb_object_agg(it.lang, it.value) AS value, bool_or(imd.noupdate) AS noupdate
                  FROM _ir_translation it
             LEFT JOIN ir_model_data imd
                    ON imd.model = %s AND imd.res_id = it.res_id AND imd.module != '__export__'
                 WHERE it.type = 'model' AND it.name = %s AND it.state = 'translated'
              GROUP BY it.res_id
            )
            UPDATE {Model._table} m
               SET "{field.name}" = CASE WHEN m."{field.name}" IS NULL THEN {emtpy_src} || t.value
                                         WHEN t.noupdate IS FALSE THEN t.value || m."{field.name}"
                                         ELSE m."{field.name}" || t.value
                                     END
              FROM t
             WHERE t.res_id = m.id
        """
        migrate_queries.append(cr.mogrify(query, [Model._name, translation_name]).decode())

        query = "DELETE FROM _ir_translation WHERE type = 'model' AND name = %s"
        cleanup_queries.append(cr.mogrify(query, [translation_name]).decode())

    # upgrade model_terms translation: one update per field per record
    if callable(field.translate):
        cr.execute("SELECT code FROM res_lang WHERE active = 't'")
        languages = {l[0] for l in cr.fetchall()}
        query = f"""
            SELECT t.res_id, m."{field.name}", t.value, t.noupdate
              FROM t
              JOIN "{Model._table}" m ON t.res_id = m.id
        """
        if translation_name == 'ir.ui.view,arch_db':
            cr.execute("SELECT id from ir_module_module WHERE name = 'website' AND state='installed'")
            if cr.fetchone():
                query = f"""
                    SELECT t.res_id, m."{field.name}", t.value, t.noupdate, l.code
                      FROM t
                      JOIN "{Model._table}" m ON t.res_id = m.id
                      JOIN website w ON m.website_id = w.id
                      JOIN res_lang l ON w.default_lang_id = l.id
                    UNION
                    SELECT t.res_id, m."{field.name}", t.value, t.noupdate, 'en_US'
                      FROM t
                      JOIN "{Model._table}" m ON t.res_id = m.id
                     WHERE m.website_id IS NULL
                """
        cr.execute(f"""
            WITH t0 AS (
                -- aggregate translations by source term --
                SELECT res_id, lang, jsonb_object_agg(src, value) AS value
                  FROM _ir_translation
                 WHERE type = 'model_terms' AND name = %s AND state = 'translated'
              GROUP BY res_id, lang
            ),
            t AS (
                -- aggregate translations by lang --
                SELECT t0.res_id AS res_id, jsonb_object_agg(t0.lang, t0.value) AS value, bool_or(imd.noupdate) AS noupdate
                  FROM t0
             LEFT JOIN ir_model_data imd
                    ON imd.model = %s AND imd.res_id = t0.res_id
              GROUP BY t0.res_id
            )""" + query, [translation_name, Model._name])
        for id_, new_translations, translations, noupdate, *extra in cr.fetchall():
            if not new_translations:
                continue
            # new_translations contains translations updated from the latest po files
            src_value = new_translations.pop('en_US')
            src_terms = field.get_trans_terms(src_value)
            for lang, dst_value in new_translations.items():
                terms_mapping = translations.setdefault(lang, {})
                dst_terms = field.get_trans_terms(dst_value)
                for src_term, dst_term in zip(src_terms, dst_terms):
                    if src_term == dst_term or noupdate:
                        terms_mapping.setdefault(src_term, dst_term)
                    else:
                        terms_mapping[src_term] = dst_term
            new_values = {
                lang: field.translate(terms_mapping.get, src_value)
                for lang, terms_mapping in translations.items()
            }
            if "en_US" not in new_values:
                new_values["en_US"] = field.translate(lambda v: None, src_value)
            if extra and extra[0] not in new_values:
                new_values[extra[0]] = field.translate(lambda v: None, src_value)
            elif not extra:
                missing_languages = languages - set(translations)
                if missing_languages:
                    src_value = field.translate(lambda v: None, src_value)
                    for lang in sorted(missing_languages):
                        new_values[lang] = src_value
            query = f'UPDATE "{Model._table}" SET "{field.name}" = %s WHERE id = %s'
            migrate_queries.append(cr.mogrify(query, [Json(new_values), id_]).decode())

        query = "DELETE FROM _ir_translation WHERE type = 'model_terms' AND name = %s"
        cleanup_queries.append(cr.mogrify(query, [translation_name]).decode())

    return migrate_queries, cleanup_queries
