# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import codecs
import csv
import fnmatch
import inspect
import locale
import logging
import os
import re
import tarfile
import tempfile
import threading
from collections import defaultdict
from datetime import datetime
from os.path import join
from xml.sax.saxutils import escape

from babel.messages import extract
from lxml import etree

import odoo
from odoo.tools import config
from odoo.tools.misc import file_open, get_iso_codes, SKIPPED_ELEMENT_TYPES
from odoo.tools.osutil import walksymlinks
from odoo import sql_db, SUPERUSER_ID

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
    'id_ID': 'Indonesian_indonesia',
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
    #should find more specific locales for spanish countries,
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

# These are not all english small words, just those that could potentially be isolated within views
ENGLISH_SMALL_WORDS = set("as at by do go if in me no of ok on or to up us we".split())


class UNIX_LINE_TERMINATOR(csv.excel):
    lineterminator = '\n'

csv.register_dialect("UNIX", UNIX_LINE_TERMINATOR)


#
# Helper functions for translating fields
#
def encode(s):
    if isinstance(s, unicode):
        return s.encode('utf8')
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
    'string', 'help', 'sum', 'avg', 'confirm', 'placeholder', 'alt', 'title',
}

avoid_pattern = re.compile(r"[\s\n]*<!DOCTYPE", re.IGNORECASE)

class XMLTranslator(object):
    """ A sequence of serialized XML/HTML items, with some of them to translate
        (todo) and others already translated (done). The purpose of this object
        is to simplify the handling of phrasing elements (like <b>) that must be
        translated together with their surrounding text.

        For instance, the content of the "div" element below will be translated
        as a whole (without surrounding spaces):

            <div>
                Lorem ipsum dolor sit amet, consectetur adipiscing elit,
                <b>sed</b> do eiusmod tempor incididunt ut labore et dolore
                magna aliqua. <span class="more">Ut enim ad minim veniam,
                <em>quis nostrud exercitation</em> ullamco laboris nisi ut
                aliquip ex ea commodo consequat.</span>
            </div>

    """
    def __init__(self, callback, method, parser=None):
        self.callback = callback        # callback function to translate terms
        self.method = method            # serialization method ('xml' or 'html')
        self.parser = parser            # parser for validating translations
        self._done = []                 # translated strings
        self._todo = []                 # todo strings that come after _done
        self.needs_trans = False        # whether todo needs translation

    def todo(self, text, needs_trans=True):
        self._todo.append(text)
        if needs_trans and text.strip():
            self.needs_trans = True

    def all_todo(self):
        return not self._done

    def get_todo(self):
        return "".join(self._todo)

    def flush(self):
        if self._todo:
            todo = "".join(self._todo)
            done = self.process_text(todo) if self.needs_trans else todo
            self._done.append(done)
            del self._todo[:]
            self.needs_trans = False

    def done(self, text):
        self.flush()
        self._done.append(text)

    def get_done(self):
        """ Complete the translations and return the result. """
        self.flush()
        return "".join(self._done)

    def process_text(self, text):
        """ Translate text.strip(), but keep the surrounding spaces from text. """
        term = text.strip()
        trans = term and self.callback(term)
        if trans:
            try:
                # parse the translation to validate it
                etree.fromstring("<div>%s</div>" % encode(trans), parser=self.parser)
            except etree.ParseError:
                # fallback: escape the translation
                trans = escape(trans)
            text = text.replace(term, trans)
        return text

    def process_attr(self, attr):
        """ Translate the given node attribute value. """
        term = attr.strip()
        trans = term and self.callback(term)
        return attr.replace(term, trans) if trans else attr

    def process(self, node):
        """ Process the given xml `node`: collect `todo` and `done` items. """
        if (
            isinstance(node, SKIPPED_ELEMENT_TYPES) or
            node.tag in SKIPPED_ELEMENTS or
            node.get("t-translation", "").strip() == "off" or
            node.tag == "attribute" and node.get("name") not in TRANSLATED_ATTRS or
            node.getparent() is None and node.text and '<!DOCTYPE' in node.text
        ):
            # do not translate the contents of the node
            tail, node.tail = node.tail, None
            self.done(etree.tostring(node, method=self.method))
            self.todo(escape(tail or ""))
            return

        # process children nodes locally in child_trans
        child_trans = XMLTranslator(self.callback, self.method, parser=self.parser)
        if node.text:
            if avoid_pattern.match(node.text):
                child_trans.done(escape(node.text)) # do not translate <!DOCTYPE...
            else:
                child_trans.todo(escape(node.text))
        for child in node:
            child_trans.process(child)

        if (child_trans.all_todo() and
                node.tag in TRANSLATED_ELEMENTS and
                not any(attr.startswith("t-") for attr in node.attrib)):
            # serialize the node element as todo
            self.todo(self.serialize(node.tag, node.attrib, child_trans.get_todo()),
                      child_trans.needs_trans)
        else:
            # complete translations and serialize result as done
            for attr in TRANSLATED_ATTRS:
                if node.get(attr):
                    node.set(attr, self.process_attr(node.get(attr)))
            self.done(self.serialize(node.tag, node.attrib, child_trans.get_done()))

        # add node tail as todo
        self.todo(escape(node.tail or ""))

    def serialize(self, tag, attrib, content):
        """ Return a serialized element with the given `tag`, attributes
            `attrib`, and already-serialized `content`.
        """
        if content:
            elem = etree.tostring(etree.Element(tag, attrib), method='xml')
            assert elem.endswith("/>")
            return "%s>%s</%s>" % (elem[:-2], content, tag)
        else:
            return etree.tostring(etree.Element(tag, attrib), method=self.method)


def xml_translate(callback, value):
    """ Translate an XML value (string), using `callback` for translating text
        appearing in `value`.
    """
    if not value:
        return value

    trans = XMLTranslator(callback, 'xml')
    try:
        root = etree.fromstring(encode(value))
        trans.process(root)
        return trans.get_done()
    except etree.ParseError:
        # fallback for translated terms: use an HTML parser and wrap the term
        wrapped = "<div>%s</div>" % encode(value)
        root = etree.fromstring(wrapped, etree.HTMLParser(encoding='utf-8'))
        trans.process(root[0][0])               # html > body > div
        return trans.get_done()[5:-6]           # remove tags <div> and </div>

def html_translate(callback, value):
    """ Translate an HTML value (string), using `callback` for translating text
        appearing in `value`.
    """
    if not value:
        return value

    try:
        parser = etree.HTMLParser(encoding='utf-8')
        trans = XMLTranslator(callback, 'html', parser)
        wrapped = "<div>%s</div>" % encode(value)
        root = etree.fromstring(wrapped, parser)
        trans.process(root[0][0])               # html > body > div
        value = trans.get_done()[5:-6]           # remove tags <div> and </div>
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

class GettextAlias(object):

    def _get_db(self):
        # find current DB based on thread/worker db name (see netsvc)
        db_name = getattr(threading.currentThread(), 'dbname', None)
        if db_name:
            return sql_db.db_connect(db_name)

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
                #          don't know the originial uid, so the language may
                #          be wrong when the admin language differs.
                (cr, dummy) = self._get_cr(frame, allow_create=False)
                uid = self._get_uid(frame)
                if cr and uid:
                    env = odoo.api.Environment(cr, uid, {})
                    lang = env['res.users'].context_get()['lang']
        return lang

    def __call__(self, source):
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
            lang = self._get_lang(frame)
            if lang:
                cr, is_new_cr = self._get_cr(frame)
                if cr:
                    # Try to use ir.translation to benefit from global cache if possible
                    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
                    res = env['ir.translation']._get_source(None, ('code','sql_constraint'), lang, source)
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
        return res

_ = GettextAlias()


def quote(s):
    """Returns quoted PO term string, with special PO characters escaped"""
    assert r"\n" not in s, "Translation terms may not include escaped newlines ('\\n'), please use only literal newlines! (in '%s')" % s
    return '"%s"' % s.replace('\\','\\\\') \
                     .replace('"','\\"') \
                     .replace('\n', '\\n"\n"')

re_escaped_char = re.compile(r"(\\.)")
re_escaped_replacements = {'n': '\n', }

def _sub_replacement(match_obj):
    return re_escaped_replacements.get(match_obj.group(1)[1], match_obj.group(1)[1])

def unquote(str):
    """Returns unquoted PO term string, with special PO characters unescaped"""
    return re_escaped_char.sub(_sub_replacement, str[1:-1])

# class to handle po files
class PoFile(object):
    def __init__(self, buffer):
        self.buffer = buffer

    def __iter__(self):
        self.buffer.seek(0)
        self.lines = self._get_lines()
        self.lines_count = len(self.lines)

        self.first = True
        self.extra_lines= []
        return self

    def _get_lines(self):
        lines = self.buffer.readlines()
        # remove the BOM (Byte Order Mark):
        if len(lines):
            lines[0] = unicode(lines[0], 'utf8').lstrip(unicode( codecs.BOM_UTF8, "utf8"))

        lines.append('') # ensure that the file ends with at least an empty line
        return lines

    def cur_line(self):
        return self.lines_count - len(self.lines)

    def next(self):
        trans_type = name = res_id = source = trad = None
        if self.extra_lines:
            trans_type, name, res_id, source, trad, comments = self.extra_lines.pop(0)
            if not res_id:
                res_id = '0'
        else:
            comments = []
            targets = []
            line = None
            fuzzy = False
            while not line:
                if 0 == len(self.lines):
                    raise StopIteration()
                line = self.lines.pop(0).strip()
            while line.startswith('#'):
                if line.startswith('#~ '):
                    break
                if line.startswith('#.'):
                    line = line[2:].strip()
                    if not line.startswith('module:'):
                        comments.append(line)
                elif line.startswith('#:'):
                    # Process the `reference` comments. Each line can specify
                    # multiple targets (e.g. model, view, code, selection,
                    # ...). For each target, we will return an additional
                    # entry.
                    for lpart in line[2:].strip().split(' '):
                        trans_info = lpart.strip().split(':',2)
                        if trans_info and len(trans_info) == 2:
                            # looks like the translation trans_type is missing, which is not
                            # unexpected because it is not a GetText standard. Default: 'code'
                            trans_info[:0] = ['code']
                        if trans_info and len(trans_info) == 3:
                            # this is a ref line holding the destination info (model, field, record)
                            targets.append(trans_info)
                elif line.startswith('#,') and (line[2:].strip() == 'fuzzy'):
                    fuzzy = True
                line = self.lines.pop(0).strip()
            if not self.lines:
                raise StopIteration()
            while not line:
                # allow empty lines between comments and msgid
                line = self.lines.pop(0).strip()
            if line.startswith('#~ '):
                while line.startswith('#~ ') or not line.strip():
                    if 0 == len(self.lines):
                        raise StopIteration()
                    line = self.lines.pop(0)
                # This has been a deprecated entry, don't return anything
                return self.next()

            if not line.startswith('msgid'):
                raise Exception("malformed file: bad line: %s" % line)
            source = unquote(line[6:])
            line = self.lines.pop(0).strip()
            if not source and self.first:
                self.first = False
                # if the source is "" and it's the first msgid, it's the special
                # msgstr with the informations about the traduction and the
                # traductor; we skip it
                self.extra_lines = []
                while line:
                    line = self.lines.pop(0).strip()
                return self.next()

            while not line.startswith('msgstr'):
                if not line:
                    raise Exception('malformed file at %d'% self.cur_line())
                source += unquote(line)
                line = self.lines.pop(0).strip()

            trad = unquote(line[7:])
            line = self.lines.pop(0).strip()
            while line:
                trad += unquote(line)
                line = self.lines.pop(0).strip()

            if targets and not fuzzy:
                # Use the first target for the current entry (returned at the
                # end of this next() call), and keep the others to generate
                # additional entries (returned the next next() calls).
                trans_type, name, res_id = targets.pop(0)
                for t, n, r in targets:
                    if t == trans_type == 'code': continue
                    self.extra_lines.append((t, n, r, source, trad, comments))

        if name is None:
            if not fuzzy:
                _logger.warning('Missing "#:" formated comment at line %d for the following source:\n\t%s',
                                self.cur_line(), source[:30])
            return self.next()
        return trans_type, name, res_id, source, trad, '\n'.join(comments)

    def write_infos(self, modules):
        import odoo.release as release
        self.buffer.write("# Translation of %(project)s.\n" \
                          "# This file contains the translation of the following modules:\n" \
                          "%(modules)s" \
                          "#\n" \
                          "msgid \"\"\n" \
                          "msgstr \"\"\n" \
                          '''"Project-Id-Version: %(project)s %(version)s\\n"\n''' \
                          '''"Report-Msgid-Bugs-To: \\n"\n''' \
                          '''"POT-Creation-Date: %(now)s\\n"\n'''        \
                          '''"PO-Revision-Date: %(now)s\\n"\n'''         \
                          '''"Last-Translator: <>\\n"\n''' \
                          '''"Language-Team: \\n"\n'''   \
                          '''"MIME-Version: 1.0\\n"\n''' \
                          '''"Content-Type: text/plain; charset=UTF-8\\n"\n'''   \
                          '''"Content-Transfer-Encoding: \\n"\n'''       \
                          '''"Plural-Forms: \\n"\n'''    \
                          "\n"

                          % { 'project': release.description,
                              'version': release.version,
                              'modules': reduce(lambda s, m: s + "#\t* %s\n" % m, modules, ""),
                              'now': datetime.utcnow().strftime('%Y-%m-%d %H:%M')+"+0000",
                            }
                          )

    def write(self, modules, tnrs, source, trad, comments=None):

        plurial = len(modules) > 1 and 's' or ''
        self.buffer.write("#. module%s: %s\n" % (plurial, ', '.join(modules)))

        if comments:
            self.buffer.write(''.join(('#. %s\n' % c for c in comments)))

        code = False
        for typy, name, res_id in tnrs:
            self.buffer.write("#: %s:%s:%s\n" % (typy, name, res_id))
            if typy == 'code':
                code = True

        if code:
            # only strings in python code are python formated
            self.buffer.write("#, python-format\n")

        if not isinstance(trad, unicode):
            trad = unicode(trad, 'utf8')
        if not isinstance(source, unicode):
            source = unicode(source, 'utf8')

        msg = "msgid %s\n"      \
              "msgstr %s\n\n"   \
                  % (quote(source), quote(trad))
        self.buffer.write(msg.encode('utf8'))


# Methods to export the translation file

def trans_export(lang, modules, buffer, format, cr):

    def _process(format, modules, rows, buffer, lang):
        if format == 'csv':
            writer = csv.writer(buffer, 'UNIX')
            # write header first
            writer.writerow(("module","type","name","res_id","src","value","comments"))
            for module, type, name, res_id, src, trad, comments in rows:
                comments = '\n'.join(comments)
                writer.writerow((module, type, name, res_id, src, trad, comments))

        elif format == 'po':
            writer = PoFile(buffer)
            writer.write_infos(modules)

            # we now group the translations by source. That means one translation per source.
            grouped_rows = {}
            for module, type, name, res_id, src, trad, comments in rows:
                row = grouped_rows.setdefault(src, {})
                row.setdefault('modules', set()).add(module)
                if not row.get('translation') and trad != src:
                    row['translation'] = trad
                row.setdefault('tnrs', []).append((type, name, res_id))
                row.setdefault('comments', set()).update(comments)

            for src, row in sorted(grouped_rows.items()):
                if not lang:
                    # translation template, so no translation value
                    row['translation'] = ''
                elif not row.get('translation'):
                    row['translation'] = src
                writer.write(row['modules'], row['tnrs'], src, row['translation'], row['comments'])

        elif format == 'tgz':
            rows_by_module = {}
            for row in rows:
                module = row[0]
                rows_by_module.setdefault(module, []).append(row)
            tmpdir = tempfile.mkdtemp()
            for mod, modrows in rows_by_module.items():
                tmpmoddir = join(tmpdir, mod, 'i18n')
                os.makedirs(tmpmoddir)
                pofilename = (lang if lang else mod) + ".po" + ('t' if not lang else '')
                buf = file(join(tmpmoddir, pofilename), 'w')
                _process('po', [mod], modrows, buf, lang)
                buf.close()

            tar = tarfile.open(fileobj=buffer, mode='w|gz')
            tar.add(tmpdir, '')
            tar.close()

        else:
            raise Exception(_('Unrecognized extension: must be one of '
                '.csv, .po, or .tgz (received .%s).') % format)

    translations = trans_generate(lang, modules, cr)
    modules = set(t[0] for t in translations)
    _process(format, modules, translations, buffer, lang)
    del translations


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
    term = (term or "").strip().encode('utf8')
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
        'workflow': 'base',
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
            for att in ('title', 'alt', 'label', 'placeholder'):
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


def trans_generate(lang, modules, cr):
    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
    to_translate = set()

    def push_translation(module, type, name, id, source, comments=None):
        # empty and one-letter terms are ignored, they probably are not meant to be
        # translated, and would be very hard to translate anyway.
        sanitized_term = (source or '').strip()
        try:
            # verify the minimal size without eventual xml tags
            # wrap to make sure html content like '<a>b</a><c>d</c>' is accepted by lxml
            wrapped = "<div>%s</div>" % sanitized_term
            node = etree.fromstring(wrapped)
            sanitized_term = etree.tostring(node, encoding='UTF-8', method='text')
        except etree.ParseError:
            pass
        # remove non-alphanumeric chars
        sanitized_term = re.sub(r'\W+', '', sanitized_term)
        if not sanitized_term or len(sanitized_term) <= 1:
            return

        tnx = (module, source, name, id, type, tuple(comments or ()))
        to_translate.add(tnx)

    query = 'SELECT name, model, res_id, module FROM ir_model_data'
    query_models = """SELECT m.id, m.model, imd.module
                      FROM ir_model AS m, ir_model_data AS imd
                      WHERE m.id = imd.res_id AND imd.model = 'ir.model'"""

    if 'all_installed' in modules:
        query += ' WHERE module IN ( SELECT name FROM ir_module_module WHERE state = \'installed\') '
        query_models += " AND imd.module in ( SELECT name FROM ir_module_module WHERE state = 'installed') "

    if 'all' not in modules:
        query += ' WHERE module IN %s'
        query_models += ' AND imd.module IN %s'
        query_param = (tuple(modules),)
    else:
        query += ' WHERE module != %s'
        query_models += ' AND imd.module != %s'
        query_param = ('__export__',)

    query += ' ORDER BY module, model, name'
    query_models += ' ORDER BY module, model'

    cr.execute(query, query_param)

    for (xml_name, model, res_id, module) in cr.fetchall():
        module = encode(module)
        model = encode(model)
        xml_name = "%s.%s" % (module, encode(xml_name))

        if model not in env:
            _logger.error("Unable to find object %r", model)
            continue

        record = env[model].browse(res_id)
        if not record._translate:
            # explicitly disabled
            continue

        if not record.exists():
            _logger.warning("Unable to find object %r with id %d", model, res_id)
            continue

        if model=='ir.model.fields':
            try:
                field_name = encode(record.name)
            except AttributeError, exc:
                _logger.error("name error in %s: %s", xml_name, str(exc))
                continue
            field_model = env.get(record.model)
            if (field_model is None or not field_model._translate or
                    field_name not in field_model._fields):
                continue
            field = field_model._fields[field_name]

            if isinstance(getattr(field, 'selection', None), (list, tuple)):
                name = "%s,%s" % (encode(record.model), field_name)
                for dummy, val in field.selection:
                    push_translation(module, 'selection', name, 0, encode(val))

        elif model=='ir.actions.report.xml':
            name = encode(record.report_name)
            fname = ""
            if record.report_rml:
                fname = record.report_rml
                parse_func = trans_parse_rml
                report_type = "report"
            elif record.report_xsl:
                continue
            if fname and record.report_type in ('pdf', 'xsl'):
                try:
                    with file_open(fname) as report_file:
                        d = etree.parse(report_file)
                        for t in parse_func(d.iter()):
                            push_translation(module, report_type, name, 0, t)
                except (IOError, etree.XMLSyntaxError):
                    _logger.exception("couldn't export translation for report %s %s %s", name, report_type, fname)

        for field_name, field in record._fields.iteritems():
            if field.translate:
                name = model + "," + field_name
                try:
                    value = record[field_name] or ''
                except Exception:
                    continue
                for term in set(field.get_trans_terms(value)):
                    push_translation(module, 'model', name, xml_name, encode(term))

        # End of data for ir.model.data query results

    def push_constraint_msg(module, term_type, model, msg):
        if not callable(msg):
            push_translation(encode(module), term_type, encode(model), 0, encode(msg))

    def push_local_constraints(module, model, cons_type='sql_constraints'):
        """ Climb up the class hierarchy and ignore inherited constraints from other modules. """
        term_type = 'sql_constraint' if cons_type == 'sql_constraints' else 'constraint'
        msg_pos = 2 if cons_type == 'sql_constraints' else 1
        for cls in model.__class__.__mro__:
            if getattr(cls, '_module', None) != module:
                continue
            constraints = getattr(cls, '_local_' + cons_type, [])
            for constraint in constraints:
                push_constraint_msg(module, term_type, model._name, constraint[msg_pos])
            
    cr.execute(query_models, query_param)

    for (_, model, module) in cr.fetchall():
        if model not in env:
            _logger.error("Unable to find object %r", model)
            continue
        Model = env[model]
        if Model._constraints:
            push_local_constraints(module, Model, 'constraints')
        if Model._sql_constraints:
            push_local_constraints(module, Model, 'sql_constraints')

    installed_modules = [
        m['name']
        for m in env['ir.module.module'].search_read([('state', '=', 'installed')], fields=['name'])
    ]

    path_list = [(path, True) for path in odoo.modules.module.ad_paths]
    # Also scan these non-addon paths
    for bin_path in ['osv', 'report', 'modules', 'service', 'tools']:
        path_list.append((os.path.join(config['root_path'], bin_path), True))
    # non-recursive scan for individual files in root directory but without
    # scanning subdirectories that may contain addons
    path_list.append((config['root_path'], False))
    _logger.debug("Scanning modules at paths: %s", path_list)

    def get_module_from_path(path):
        for (mp, rec) in path_list:
            mp = os.path.join(mp, '')
            dirname = os.path.join(os.path.dirname(path), '')
            if rec and path.startswith(mp) and dirname != mp:
                path = path[len(mp):]
                return path.split(os.path.sep)[0]
        return 'base' # files that are not in a module are considered as being in 'base' module

    def verified_module_filepaths(fname, path, root):
        fabsolutepath = join(root, fname)
        frelativepath = fabsolutepath[len(path):]
        display_path = "addons%s" % frelativepath
        module = get_module_from_path(fabsolutepath)
        if ('all' in modules or module in modules) and module in installed_modules:
            if os.path.sep != '/':
                display_path = display_path.replace(os.path.sep, '/')
            return module, fabsolutepath, frelativepath, display_path
        return None, None, None, None

    def babel_extract_terms(fname, path, root, extract_method="python", trans_type='code',
                               extra_comments=None, extract_keywords={'_': None}):
        module, fabsolutepath, _, display_path = verified_module_filepaths(fname, path, root)
        extra_comments = extra_comments or []
        if not module: return
        src_file = open(fabsolutepath, 'r')
        try:
            for extracted in extract.extract(extract_method, src_file, keywords=extract_keywords):
                # Babel 0.9.6 yields lineno, message, comments
                # Babel 1.3 yields lineno, message, comments, context
                lineno, message, comments = extracted[:3]
                push_translation(module, trans_type, display_path, lineno,
                                 encode(message), comments + extra_comments)
        except Exception:
            _logger.exception("Failed to extract terms from %s", fabsolutepath)
        finally:
            src_file.close()

    for (path, recursive) in path_list:
        _logger.debug("Scanning files of modules at %s", path)
        for root, dummy, files in walksymlinks(path):
            for fname in fnmatch.filter(files, '*.py'):
                babel_extract_terms(fname, path, root)
            # mako provides a babel extractor: http://docs.makotemplates.org/en/latest/usage.html#babel
            for fname in fnmatch.filter(files, '*.mako'):
                babel_extract_terms(fname, path, root, 'mako', trans_type='report')
            # Javascript source files in the static/src/js directory, rest is ignored (libs)
            if fnmatch.fnmatch(root, '*/static/src/js*'):
                for fname in fnmatch.filter(files, '*.js'):
                    babel_extract_terms(fname, path, root, 'javascript',
                                        extra_comments=[WEB_TRANSLATION_COMMENT],
                                        extract_keywords={'_t': None, '_lt': None})
            # QWeb template files
            if fnmatch.fnmatch(root, '*/static/src/xml*'):
                for fname in fnmatch.filter(files, '*.xml'):
                    babel_extract_terms(fname, path, root, 'odoo.tools.translate:babel_extract_qweb',
                                        extra_comments=[WEB_TRANSLATION_COMMENT])
            if not recursive:
                # due to topdown, first iteration is in first level
                break

    out = []
    # translate strings marked as to be translated
    Translation = env['ir.translation']
    for module, source, name, id, type, comments in sorted(to_translate):
        trans = Translation._get_source(name, type, lang, source) if lang else ""
        out.append((module, type, name, id, source, encode(trans) or '', comments))
    return out


def trans_load(cr, filename, lang, verbose=True, module_name=None, context=None):
    try:
        with file_open(filename) as fileobj:
            _logger.info("loading %s", filename)
            fileformat = os.path.splitext(filename)[-1][1:].lower()
            result = trans_load_data(cr, fileobj, fileformat, lang, verbose=verbose, module_name=module_name, context=context)
            return result
    except IOError:
        if verbose:
            _logger.error("couldn't read translation file %s", filename)
        return None


def trans_load_data(cr, fileobj, fileformat, lang, lang_name=None, verbose=True, module_name=None, context=None):
    """Populates the ir_translation table."""
    if verbose:
        _logger.info('loading translation file for language %s', lang)

    env = odoo.api.Environment(cr, SUPERUSER_ID, context or {})
    Lang = env['res.lang']
    Translation = env['ir.translation']

    try:
        if not Lang.search_count([('code', '=', lang)]):
            # lets create the language with locale information
            Lang.load_lang(lang=lang, lang_name=lang_name)

        # Parse also the POT: it will possibly provide additional targets.
        # (Because the POT comments are correct on Launchpad but not the
        # PO comments due to a Launchpad limitation. See LP bug 933496.)
        pot_reader = []

        # now, the serious things: we read the language file
        fileobj.seek(0)
        if fileformat == 'csv':
            reader = csv.reader(fileobj, quotechar='"', delimiter=',')
            # read the first line of the file (it contains columns titles)
            for row in reader:
                fields = row
                break

        elif fileformat == 'po':
            reader = PoFile(fileobj)
            fields = ['type', 'name', 'res_id', 'src', 'value', 'comments']

            # Make a reader for the POT file and be somewhat defensive for the
            # stable branch.
            if fileobj.name.endswith('.po'):
                try:
                    # Normally the path looks like /path/to/xxx/i18n/lang.po
                    # and we try to find the corresponding
                    # /path/to/xxx/i18n/xxx.pot file.
                    # (Sometimes we have 'i18n_extra' instead of just 'i18n')
                    addons_module_i18n, _ignored = os.path.split(fileobj.name)
                    addons_module, i18n_dir = os.path.split(addons_module_i18n)
                    addons, module = os.path.split(addons_module)
                    pot_handle = file_open(os.path.join(
                        addons, module, i18n_dir, module + '.pot'))
                    pot_reader = PoFile(pot_handle)
                except:
                    pass

        else:
            _logger.info('Bad file format: %s', fileformat)
            raise Exception(_('Bad file format: %s') % fileformat)

        # Read the POT references, and keep them indexed by source string.
        class Target(object):
            def __init__(self):
                self.value = None
                self.targets = set()            # set of (type, name, res_id)
                self.comments = None

        pot_targets = defaultdict(Target)
        for type, name, res_id, src, _ignored, comments in pot_reader:
            if type is not None:
                target = pot_targets[src]
                target.targets.add((type, name, res_id))
                target.comments = comments

        # read the rest of the file
        irt_cursor = Translation._get_import_cursor()

        def process_row(row):
            """Process a single PO (or POT) entry."""
            # dictionary which holds values for this line of the csv file
            # {'lang': ..., 'type': ..., 'name': ..., 'res_id': ...,
            #  'src': ..., 'value': ..., 'module':...}
            dic = dict.fromkeys(('type', 'name', 'res_id', 'src', 'value',
                                 'comments', 'imd_model', 'imd_name', 'module'))
            dic['lang'] = lang
            dic.update(zip(fields, row))

            # discard the target from the POT targets.
            src = dic['src']
            if src in pot_targets:
                target = pot_targets[src]
                target.value = dic['value']
                target.targets.discard((dic['type'], dic['name'], dic['res_id']))

            # This would skip terms that fail to specify a res_id
            res_id = dic['res_id']
            if not res_id:
                return

            if isinstance(res_id, (int, long)) or \
                    (isinstance(res_id, basestring) and res_id.isdigit()):
                dic['res_id'] = int(res_id)
                if module_name:
                    dic['module'] = module_name
            else:
                # res_id is an xml id
                dic['res_id'] = None
                dic['imd_model'] = dic['name'].split(',')[0]
                if '.' in res_id:
                    dic['module'], dic['imd_name'] = res_id.split('.', 1)
                else:
                    dic['module'], dic['imd_name'] = module_name, res_id

            irt_cursor.push(dic)

        # First process the entries from the PO file (doing so also fills/removes
        # the entries from the POT file).
        for row in reader:
            process_row(row)

        # Then process the entries implied by the POT file (which is more
        # correct w.r.t. the targets) if some of them remain.
        pot_rows = []
        for src, target in pot_targets.iteritems():
            if target.value:
                for type, name, res_id in target.targets:
                    pot_rows.append((type, name, res_id, src, target.value, target.comments))
        pot_targets.clear()
        for row in pot_rows:
            process_row(row)

        irt_cursor.finish()
        Translation.clear_caches()
        if verbose:
            _logger.info("translation file loaded succesfully")

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
    env = odoo.api.Environment(cr, SUPERUSER_ID, {})
    installer = env['base.language.install'].create({'lang': lang})
    installer.lang_install()
