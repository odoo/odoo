# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import codecs
import fnmatch
import functools
import inspect
import io
import locale
import logging
import os
import polib
import re
import tarfile
import tempfile
import threading
from collections import defaultdict, namedtuple
from datetime import datetime
from os.path import join

from pathlib import Path
from babel.messages import extract
from lxml import etree, html

import odoo
from . import config, pycompat
from .misc import file_open, get_iso_codes, SKIPPED_ELEMENT_TYPES

_logger = logging.getLogger(__name__)

# used to notify web client that these translations should be loaded in the UI
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
    'tr_TR': 'Turkish_Turkey',
    'uk_UA': 'Ukrainian_Ukraine',
    'vi_VN': 'Vietnamese_Viet Nam',
    'tlh_TLH': 'Klingon',

}

# These are not all English small words, just those that could potentially be isolated within views
ENGLISH_SMALL_WORDS = set("as at by do go if in me no of ok on or to up us we".split())


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
    'sup', 'time', 'u', 'var', 'wbr', 'text',
}

# which attributes must be translated
TRANSLATED_ATTRS = {
    'string', 'help', 'sum', 'avg', 'confirm', 'placeholder', 'alt', 'title', 'aria-label',
    'aria-keyshortcuts', 'aria-placeholder', 'aria-roledescription', 'aria-valuetext',
    'value_label',
}

TRANSLATED_ATTRS = TRANSLATED_ATTRS | {'t-attf-' + attr for attr in TRANSLATED_ATTRS}

avoid_pattern = re.compile(r"\s*<!DOCTYPE", re.IGNORECASE | re.MULTILINE | re.UNICODE)
node_pattern = re.compile(r"<[^>]*>(.*)</[^<]*>", re.DOTALL | re.MULTILINE | re.UNICODE)


def translate_xml_node(node, callback, parse, serialize):
    """ Return the translation of the given XML/HTML node.

        :param callback: callback(text) returns translated text or None
        :param parse: parse(text) returns a node (text is unicode)
        :param serialize: serialize(node) returns unicode text
    """

    def nonspace(text):
        return bool(text) and len(re.sub(r'\W+', '', text)) > 1

    def concat(text1, text2):
        return text2 if text1 is None else text1 + (text2 or "")

    def append_content(node, source):
        """ Append the content of ``source`` node to ``node``. """
        if len(node):
            node[-1].tail = concat(node[-1].tail, source.text)
        else:
            node.text = concat(node.text, source.text)
        for child in source:
            node.append(child)

    def translate_text(text):
        """ Return the translation of ``text`` (the term to translate is without
            surrounding spaces), or a falsy value if no translation applies.
        """
        term = text.strip()
        trans = term and callback(term)
        return trans and text.replace(term, trans)

    def translate_content(node):
        """ Return ``node`` with its content translated inline. """
        # serialize the node that contains the stuff to translate
        text = serialize(node)
        # retrieve the node's content and translate it
        match = node_pattern.match(text)
        trans = translate_text(match.group(1))
        if trans:
            # replace the content, and convert it back to an XML node
            text = text[:match.start(1)] + trans + text[match.end(1):]
            try:
                node = parse(text)
            except etree.ParseError:
                # fallback: escape the translation as text
                node = etree.Element(node.tag, node.attrib, node.nsmap)
                node.text = trans
        return node

    def process(node):
        """ If ``node`` can be translated inline, return ``(has_text, node)``,
            where ``has_text`` is a boolean that tells whether ``node`` contains
            some actual text to translate. Otherwise return ``(None, result)``,
            where ``result`` is the translation of ``node`` except for its tail.
        """
        if (
            isinstance(node, SKIPPED_ELEMENT_TYPES) or
            node.tag in SKIPPED_ELEMENTS or
            node.get('t-translation', "").strip() == "off" or
            node.tag == 'attribute' and node.get('name') not in TRANSLATED_ATTRS or
            node.getparent() is None and avoid_pattern.match(node.text or "")
        ):
            return (None, node)

        # make an element like node that will contain the result
        result = etree.Element(node.tag, node.attrib, node.nsmap)

        # use a "todo" node to translate content by parts
        todo = etree.Element('div', nsmap=node.nsmap)
        if avoid_pattern.match(node.text or ""):
            result.text = node.text
        else:
            todo.text = node.text
        todo_has_text = nonspace(todo.text)

        # process children recursively
        for child in node:
            child_has_text, child = process(child)
            if child_has_text is None:
                # translate the content of todo and append it to result
                append_content(result, translate_content(todo) if todo_has_text else todo)
                # add translated child to result
                result.append(child)
                # move child's untranslated tail to todo
                todo = etree.Element('div', nsmap=node.nsmap)
                todo.text, child.tail = child.tail, None
                todo_has_text = nonspace(todo.text)
            else:
                # child is translatable inline; add it to todo
                todo.append(child)
                todo_has_text = todo_has_text or child_has_text

        # determine whether node is translatable inline
        if (
            node.tag in TRANSLATED_ELEMENTS and
            not (result.text or len(result)) and
            not any(name.startswith("t-") for name in node.attrib)
        ):
            # complete result and return it
            append_content(result, todo)
            result.tail = node.tail
            has_text = (
                todo_has_text or nonspace(result.text) or nonspace(result.tail)
                or any((key in TRANSLATED_ATTRS and val) for key, val in result.attrib.items())
            )
            return (has_text, result)

        # translate the content of todo and append it to result
        append_content(result, translate_content(todo) if todo_has_text else todo)

        # translate the required attributes
        for name, value in result.attrib.items():
            if name in TRANSLATED_ATTRS:
                result.set(name, translate_text(value) or value)

        # add the untranslated tail to result
        result.tail = node.tail

        return (None, result)

    has_text, node = process(node)
    if has_text is True:
        # translate the node as a whole
        wrapped = etree.Element('div')
        wrapped.append(node)
        return translate_content(wrapped)[0]

    return node


def parse_xml(text):
    return etree.fromstring(text)

def serialize_xml(node):
    return etree.tostring(node, method='xml', encoding='unicode')

_HTML_PARSER = etree.HTMLParser(encoding='utf8')

def parse_html(text):
    return html.fragment_fromstring(text, parser=_HTML_PARSER)

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
        value = serialize_html(result)[5:-6]
    except ValueError:
        _logger.exception("Cannot translate malformed HTML, using source value instead")

    return value


#
# Warning: better use self.env['ir.translation']._get_source if you can
#
def translate(cr, name, source_type, lang, source=None):
    if source and name:
        cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s and src=%s and md5(src)=md5(%s)', (lang, source_type, str(name), source, source))
    elif name:
        cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s', (lang, source_type, str(name)))
    elif source:
        cr.execute('select value from ir_translation where lang=%s and type=%s and src=%s and md5(src)=md5(%s)', (lang, source_type, source, source))
    res_trans = cr.fetchone()
    res = res_trans and res_trans[0] or False
    return res

def translate_sql_constraint(cr, key, lang):
    cr.execute("""
        SELECT COALESCE(t.value, c.message) as message
        FROM ir_model_constraint c
        LEFT JOIN
        (SELECT res_id, value FROM ir_translation
         WHERE type='model'
           AND name='ir.model.constraint,message'
           AND lang=%s
           AND value!='') AS t
        ON c.id=t.res_id
        WHERE name=%s and type='u'
        """, (lang, key))
    return cr.fetchone()[0]

class GettextAlias(object):

    def _get_db(self):
        # find current DB based on thread/worker db name (see netsvc)
        db_name = getattr(threading.currentThread(), 'dbname', None)
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
            try:
                return translation % (args or kwargs)
            except (TypeError, ValueError, KeyError):
                bad = translation
                # fallback: apply to source before logging exception (in case source fails)
                translation = source % (args or kwargs)
                _logger.exception('Bad translation %r for string %r', bad, source)
        return translation

    def _get_translation(self, source):
        res = source
        cr = None
        is_new_cr = False
        try:
            frame = inspect.currentframe()
            if frame is None:
                return source
            frame = frame.f_back
            if not frame:
                return source
            frame = frame.f_back
            if not frame:
                return source
            lang = self._get_lang(frame)
            if lang:
                cr, is_new_cr = self._get_cr(frame)
                if cr:
                    # Try to use ir.translation to benefit from global cache if possible
                    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                    res = env['ir.translation']._get_source(None, ('code',), lang, source)
                else:
                    _logger.debug('no context cursor detected, skipping translation for "%r"', source)
            else:
                _logger.debug('no translation language detected, skipping translation for "%r" ', source)
        except Exception:
            _logger.debug('translation went wrong for "%r", skipped', source)
                # if so, double-check the root/base translations filenames
        finally:
            if cr and is_new_cr:
                cr.close()
        return res or ''


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

    __slots__ = ['_source', '_args']
    def __init__(self, source, *args, **kwargs):
        self._source = source
        assert not (args and kwargs)
        self._args = args or kwargs

    def __str__(self):
        # Call _._get_translation() like _() does, so that we have the same number
        # of stack frames calling _get_translation()
        translation = _._get_translation(self._source)
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
            entry["imd_model"] = entry["name"].split(":")[0]

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
        modules = set([])
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
            self.add_entry(row['modules'], sorted(row['tnrs']), src, row['translation'], row['comments'])

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


def trans_parse_rml(de):
    res = []
    for n in de:
        for m in n:
            if isinstance(m, SKIPPED_ELEMENT_TYPES) or not m.text:
                continue
            string_list = [s.replace('\n', ' ').strip() for s in re.split('\[\[.+?\]\]', m.text)]
            for s in string_list:
                if s:
                    res.append(s.encode("utf8"))
        res.extend(trans_parse_rml(n))
    return res


def _push(callback, term, source_line):
    """ Sanity check before pushing translation terms """
    term = (term or "").strip()
    # Avoid non-char tokens like ':' '...' '.00' etc.
    if len(term) > 8 or any(x.isalpha() for x in term):
        callback(term, source_line)


# tests whether an object is in a list of modules
def in_modules(object_name, modules):
    if 'all' in modules:
        return True

    module_dict = {
        'ir': 'base',
        'res': 'base',
    }
    module = object_name.split('.')[0]
    module = module_dict.get(module, module)
    return module in modules


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
                and el.get("t-translation", '').strip() != "off"):

            _push(callback, el.text, el.sourceline)
            # Do not export terms contained on the Component directive of OWL
            # attributes in this context are most of the time variables,
            # not real HTML attributes.
            # Node tags starting with a capital letter are considered OWL Components
            # and a widespread convention and good practice for DOM tags is to write
            # them all lower case.
            # https://www.w3schools.com/html/html5_syntax.asp
            # https://github.com/odoo/owl/blob/master/doc/reference/component.md#composition
            if not el.tag[0].isupper() and 't-component' not in el.attrib:
                for att in ('title', 'alt', 'label', 'placeholder', 'aria-label'):
                    if att in el.attrib:
                        _push(callback, el.attrib[att], el.sourceline)
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

ImdInfo = namedtuple('ExternalId', ['name', 'model', 'res_id', 'module'])


class TranslationModuleReader:
    """ Retrieve translated records per module

    :param cr: cursor to database to export
    :param modules: list of modules to filter the exported terms, can be ['all']
                    records with no external id are always ignored
    :param lang: language code to retrieve the translations
                 retrieve source terms only if not set
    """

    def __init__(self, cr, modules=None, lang=None):
        self._cr = cr
        self._modules = modules or ['all']
        self._lang = lang
        self.env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
        self._to_translate = []
        self._path_list = [(path, True) for path in odoo.addons.__path__]
        self._installed_modules = [
            m['name']
            for m in self.env['ir.module.module'].search_read([('state', '=', 'installed')], fields=['name'])
        ]

        self._export_translatable_records()
        self._export_translatable_resources()


    def __iter__(self):
        """ Export ir.translation values for all retrieved records """

        IrTranslation = self.env['ir.translation']
        for module, source, name, res_id, ttype, comments, record_id in self._to_translate:
            trans = (
                IrTranslation._get_source(name if type != "code" else None, ttype, self._lang, source, res_id=record_id)
                if self._lang
                else ""
            )
            yield (module, ttype, name, res_id, source, encode(trans) or '', comments)

    def _push_translation(self, module, ttype, name, res_id, source, comments=None, record_id=None):
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
        self._to_translate.append((module, source, name, res_id, ttype, tuple(comments or ()), record_id))

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
            records = self._get_translatable_records(imd_per_id.values())
            if not records:
                continue

            for record in records:
                xml_name = "%s.%s" % (imd_per_id[record.id].module, imd_per_id[record.id].name)
                for field_name, field in record._fields.items():
                    if field.translate:
                        name = model + "," + field_name
                        try:
                            value = record[field_name] or ''
                        except Exception:
                            continue
                        for term in set(field.get_trans_terms(value)):
                            trans_type = 'model_terms' if callable(field.translate) else 'model'
                            self._push_translation(module, trans_type, name, xml_name, term, record_id=record.id)

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
        src_file = open(fabsolutepath, 'rb')
        options = {}
        if extract_method == 'python':
            options['encoding'] = 'UTF-8'
        try:
            for extracted in extract.extract(extract_method, src_file, keywords=extract_keywords, options=options):
                # Babel 0.9.6 yields lineno, message, comments
                # Babel 1.3 yields lineno, message, comments, context
                lineno, message, comments = extracted[:3]
                self._push_translation(module, trans_type, display_path, lineno,
                                 encode(message), comments + extra_comments)
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
        """

        # Also scan these non-addon paths
        for bin_path in ['osv', 'report', 'modules', 'service', 'tools']:
            self._path_list.append((os.path.join(config['root_path'], bin_path), True))
        # non-recursive scan for individual files in root directory but without
        # scanning subdirectories that may contain addons
        self._path_list.append((config['root_path'], False))
        _logger.debug("Scanning modules at paths: %s", self._path_list)

        for (path, recursive) in self._path_list:
            _logger.debug("Scanning files of modules at %s", path)
            for root, dummy, files in os.walk(path, followlinks=True):
                for fname in fnmatch.filter(files, '*.py'):
                    self._babel_extract_terms(fname, path, root,
                                              extract_keywords={'_': None, '_lt': None})
                if fnmatch.fnmatch(root, '*/static/src*'):
                    # Javascript source files
                    for fname in fnmatch.filter(files, '*.js'):
                        self._babel_extract_terms(fname, path, root, 'javascript',
                                                  extra_comments=[WEB_TRANSLATION_COMMENT],
                                                  extract_keywords={'_t': None, '_lt': None})
                    # QWeb template files
                    for fname in fnmatch.filter(files, '*.xml'):
                        self._babel_extract_terms(fname, path, root, 'odoo.tools.translate:babel_extract_qweb',
                                                  extra_comments=[WEB_TRANSLATION_COMMENT])

                if not recursive:
                    # due to topdown, first iteration is in first level
                    break


def trans_load(cr, filename, lang, verbose=True, create_empty_translation=False, overwrite=False):
    try:
        with file_open(filename, mode='rb') as fileobj:
            _logger.info("loading %s", filename)
            fileformat = os.path.splitext(filename)[-1][1:].lower()
            return trans_load_data(cr, fileobj, fileformat, lang,
                                   verbose=verbose,
                                   create_empty_translation=create_empty_translation,
                                   overwrite=overwrite)
    except IOError:
        if verbose:
            _logger.error("couldn't read translation file %s", filename)
        return None


def trans_load_data(cr, fileobj, fileformat, lang,
                    verbose=True, create_empty_translation=False, overwrite=False):
    """Populates the ir_translation table.

    :param fileobj: buffer open to a translation file
    :param fileformat: format of the `fielobj` file, one of 'po' or 'csv'
    :param lang: language code of the translations contained in `fileobj`
                 language must be present and activated in the database
    :param verbose: increase log output
    :param create_empty_translation: create an ir.translation record, even if no value
                                     is provided in the translation entry
    :param overwrite: if an ir.translation already exists for a term, replace it with
                      the one in `fileobj`
    """
    if verbose:
        _logger.info('loading translation file for language %s', lang)

    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

    try:
        if not env['res.lang']._lang_get(lang):
            _logger.error("Couldn't read translation for lang '%s', language not found", lang)
            return None

        # now, the serious things: we read the language file
        fileobj.seek(0)
        reader = TranslationFileReader(fileobj, fileformat=fileformat)

        # read the rest of the file with a cursor-like object for fast inserting translations"
        Translation = env['ir.translation']
        irt_cursor = Translation._get_import_cursor(overwrite)

        def process_row(row):
            """Process a single PO (or POT) entry."""
            # dictionary which holds values for this line of the csv file
            # {'lang': ..., 'type': ..., 'name': ..., 'res_id': ...,
            #  'src': ..., 'value': ..., 'module':...}
            dic = dict.fromkeys(('type', 'name', 'res_id', 'src', 'value',
                                 'comments', 'imd_model', 'imd_name', 'module'))
            dic['lang'] = lang
            dic.update(row)

            # do not import empty values
            if not create_empty_translation and not dic['value']:
                return

            irt_cursor.push(dic)

        # First process the entries from the PO file (doing so also fills/removes
        # the entries from the POT file).
        for row in reader:
            process_row(row)

        irt_cursor.finish()
        Translation.clear_caches()
        if verbose:
            _logger.info("translation file loaded successfully")

    except IOError:
        iso_lang = get_iso_codes(lang)
        filename = '[lang: %s][format: %s]' % (iso_lang or 'new', fileformat)
        _logger.exception("couldn't read translation file %s", filename)


def get_locales(lang=None):
    if lang is None:
        lang = locale.getdefaultlocale()[0]

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

    :param lang: language ISO code with optional _underscore_ and l10n flavor (ex: 'fr', 'fr_BE', but not 'fr-BE')
    :type lang: str
    """
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    installer = env['base.language.install'].create({'lang': lang})
    installer.lang_install()
