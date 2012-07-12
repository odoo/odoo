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

import codecs
import csv
import fnmatch
import inspect
import itertools
import locale
import os
import openerp.pooler as pooler
import openerp.sql_db as sql_db
import re
import logging
import tarfile
import tempfile
import threading
from os.path import join

from datetime import datetime
from lxml import etree

import config
import misc
from misc import UpdateableStr
from misc import SKIPPED_ELEMENT_TYPES
import osutil
import babel.messages.pofile

_logger = logging.getLogger(__name__)

_LOCALE2WIN32 = {
    'af_ZA': 'Afrikaans_South Africa',
    'sq_AL': 'Albanian_Albania',
    'ar_SA': 'Arabic_Saudi Arabia',
    'eu_ES': 'Basque_Spain',
    'be_BY': 'Belarusian_Belarus',
    'bs_BA': 'Serbian (Latin)',
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
    'id_ID': 'Indonesian_indonesia',
    'mi_NZ': 'Maori',
    'mn': 'Cyrillic_Mongolian',
    'no_NO': 'Norwegian_Norway',
    'nn_NO': 'Norwegian-Nynorsk_Norway',
    'pl': 'Polish_Poland',
    'pt_PT': 'Portuguese_Portugal',
    'pt_BR': 'Portuguese_Brazil',
    'ro_RO': 'Romanian_Romania',
    'ru_RU': 'Russian_Russia',
    'mi_NZ': 'Maori',
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
    'mi_NZ': 'Maori',
    'tr_TR': 'Turkish_Turkey',
    'uk_UA': 'Ukrainian_Ukraine',
    'vi_VN': 'Vietnamese_Viet Nam',
    'tlh_TLH': 'Klingon',

}


class UNIX_LINE_TERMINATOR(csv.excel):
    lineterminator = '\n'

csv.register_dialect("UNIX", UNIX_LINE_TERMINATOR)

#
# Warning: better use self.pool.get('ir.translation')._get_source if you can
#
def translate(cr, name, source_type, lang, source=None):
    if source and name:
        cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s and src=%s', (lang, source_type, str(name), source))
    elif name:
        cr.execute('select value from ir_translation where lang=%s and type=%s and name=%s', (lang, source_type, str(name)))
    elif source:
        cr.execute('select value from ir_translation where lang=%s and type=%s and src=%s', (lang, source_type, source))
    res_trans = cr.fetchone()
    res = res_trans and res_trans[0] or False
    return res

class GettextAlias(object):

    def _get_db(self):
        # find current DB based on thread/worker db name (see netsvc)
        db_name = getattr(threading.currentThread(), 'dbname', None)
        if db_name:
            return sql_db.db_connect(db_name)

    def _get_cr(self, frame):
        is_new_cr = False
        cr = frame.f_locals.get('cr', frame.f_locals.get('cursor'))
        if not cr:
            s = frame.f_locals.get('self', {})
            cr = getattr(s, 'cr', None)
        if not cr:
            db = self._get_db()
            if db:
                cr = db.cursor()
                is_new_cr = True
        return cr, is_new_cr

    def _get_lang(self, frame):
        lang = None
        ctx = frame.f_locals.get('context')
        if not ctx:
            kwargs = frame.f_locals.get('kwargs')
            if kwargs is None:
                args = frame.f_locals.get('args')
                if args and isinstance(args, (list, tuple)) \
                        and isinstance(args[-1], dict):
                    ctx = args[-1]
            elif isinstance(kwargs, dict):
                ctx = kwargs.get('context')
        if ctx:
            lang = ctx.get('lang')
        if not lang:
            s = frame.f_locals.get('self', {})
            c = getattr(s, 'localcontext', None)
            if c:
                lang = c.get('lang')
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
                    pool = pooler.get_pool(cr.dbname)
                    res = pool.get('ir.translation')._get_source(cr, 1, None, ('code','sql_constraint'), lang, source)
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
class TinyPoFile(object):
    def __init__(self, buffer):
        self.buffer = buffer

    def warn(self, msg, *args):
        _logger.warning(msg, *args)

    def __iter__(self):
        self.buffer.seek(0)
        self.lines = self._get_lines()
        self.lines_count = len(self.lines);

        self.first = True
        self.tnrs= []
        return self

    def _get_lines(self):
        lines = self.buffer.readlines()
        # remove the BOM (Byte Order Mark):
        if len(lines):
            lines[0] = unicode(lines[0], 'utf8').lstrip(unicode( codecs.BOM_UTF8, "utf8"))

        lines.append('') # ensure that the file ends with at least an empty line
        return lines

    def cur_line(self):
        return (self.lines_count - len(self.lines))

    def next(self):
        type = name = res_id = source = trad = None

        if self.tnrs:
            type, name, res_id, source, trad = self.tnrs.pop(0)
            if not res_id:
                res_id = '0'
        else:
            tmp_tnrs = []
            line = None
            fuzzy = False
            while (not line):
                if 0 == len(self.lines):
                    raise StopIteration()
                line = self.lines.pop(0).strip()
            while line.startswith('#'):
                if line.startswith('#~ '):
                    break
                if line.startswith('#:'):
                    for lpart in line[2:].strip().split(' '):
                        trans_info = lpart.strip().split(':',2)
                        if trans_info and len(trans_info) == 2:
                            # looks like the translation type is missing, which is not
                            # unexpected because it is not a GetText standard. Default: 'code'
                            trans_info[:0] = ['code']
                        if trans_info and len(trans_info) == 3:
                            tmp_tnrs.append(trans_info)
                elif line.startswith('#,') and (line[2:].strip() == 'fuzzy'):
                    fuzzy = True
                line = self.lines.pop(0).strip()
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
                # if the source is "" and it's the first msgid, it's the special
                # msgstr with the informations about the traduction and the
                # traductor; we skip it
                self.tnrs = []
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

            if tmp_tnrs and not fuzzy:
                type, name, res_id = tmp_tnrs.pop(0)
                for t, n, r in tmp_tnrs:
                    self.tnrs.append((t, n, r, source, trad))

        self.first = False

        if name is None:
            if not fuzzy:
                self.warn('Missing "#:" formated comment at line %d for the following source:\n\t%s',
                        self.cur_line(), source[:30])
            return self.next()
        return type, name, res_id, source, trad

    def write_infos(self, modules):
        import openerp.release as release
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

    def write(self, modules, tnrs, source, trad):

        plurial = len(modules) > 1 and 's' or ''
        self.buffer.write("#. module%s: %s\n" % (plurial, ', '.join(modules)))


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

    def _process(format, modules, rows, buffer, lang, newlang):
        if format == 'csv':
            writer=csv.writer(buffer, 'UNIX')
            for row in rows:
                writer.writerow(row)
        elif format == 'po':
            rows.pop(0)
            writer = TinyPoFile(buffer)
            writer.write_infos(modules)

            # we now group the translations by source. That means one translation per source.
            grouped_rows = {}
            for module, type, name, res_id, src, trad in rows:
                row = grouped_rows.setdefault(src, {})
                row.setdefault('modules', set()).add(module)
                if ('translation' not in row) or (not row['translation']):
                    row['translation'] = trad
                row.setdefault('tnrs', []).append((type, name, res_id))

            for src, row in grouped_rows.items():
                writer.write(row['modules'], row['tnrs'], src, row['translation'])

        elif format == 'tgz':
            rows.pop(0)
            rows_by_module = {}
            for row in rows:
                module = row[0]
                # first row is the "header", as in csv, it will be popped
                rows_by_module.setdefault(module, [['module', 'type', 'name', 'res_id', 'src', ''],])
                rows_by_module[module].append(row)

            tmpdir = tempfile.mkdtemp()
            for mod, modrows in rows_by_module.items():
                tmpmoddir = join(tmpdir, mod, 'i18n')
                os.makedirs(tmpmoddir)
                pofilename = (newlang and mod or lang) + ".po" + (newlang and 't' or '')
                buf = file(join(tmpmoddir, pofilename), 'w')
                _process('po', [mod], modrows, buf, lang, newlang)
                buf.close()

            tar = tarfile.open(fileobj=buffer, mode='w|gz')
            tar.add(tmpdir, '')
            tar.close()

        else:
            raise Exception(_('Unrecognized extension: must be one of '
                '.csv, .po, or .tgz (received .%s).' % format))

    newlang = not bool(lang)
    if newlang:
        lang = 'en_US'
    trans = trans_generate(lang, modules, cr)
    if newlang and format!='csv':
        for trx in trans:
            trx[-1] = ''
    modules = set([t[0] for t in trans[1:]])
    _process(format, modules, trans, buffer, lang, newlang)
    del trans

def trans_parse_xsl(de):
    res = []
    for n in de:
        if n.get("t"):
            for m in n:
                if isinstance(m, SKIPPED_ELEMENT_TYPES) or not m.text:
                    continue
                l = m.text.strip().replace('\n',' ')
                if len(l):
                    res.append(l.encode("utf8"))
        res.extend(trans_parse_xsl(n))
    return res

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

def trans_parse_view(de):
    res = []
    if de.text and de.text.strip():
        res.append(de.text.strip().encode("utf8"))
    if de.tail and de.tail.strip():
        res.append(de.tail.strip().encode("utf8"))
    if de.tag == 'attribute' and de.get("name") == 'string':
        if de.text:
            res.append(de.text.encode("utf8"))
    if de.get("string"):
        res.append(de.get('string').encode("utf8"))
    if de.get("help"):
        res.append(de.get('help').encode("utf8"))
    if de.get("sum"):
        res.append(de.get('sum').encode("utf8"))
    if de.get("confirm"):
        res.append(de.get('confirm').encode("utf8"))
    for n in de:
        res.extend(trans_parse_view(n))
    return res

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

def trans_generate(lang, modules, cr):
    dbname = cr.dbname

    pool = pooler.get_pool(dbname)
    trans_obj = pool.get('ir.translation')
    model_data_obj = pool.get('ir.model.data')
    uid = 1
    l = pool.models.items()
    l.sort()

    query = 'SELECT name, model, res_id, module'    \
            '  FROM ir_model_data'

    query_models = """SELECT m.id, m.model, imd.module
            FROM ir_model AS m, ir_model_data AS imd
            WHERE m.id = imd.res_id AND imd.model = 'ir.model' """

    if 'all_installed' in modules:
        query += ' WHERE module IN ( SELECT name FROM ir_module_module WHERE state = \'installed\') '
        query_models += " AND imd.module in ( SELECT name FROM ir_module_module WHERE state = 'installed') "
    query_param = None
    if 'all' not in modules:
        query += ' WHERE module IN %s'
        query_models += ' AND imd.module in %s'
        query_param = (tuple(modules),)
    query += ' ORDER BY module, model, name'
    query_models += ' ORDER BY module, model'

    cr.execute(query, query_param)

    _to_translate = []
    def push_translation(module, type, name, id, source):
        tuple = (module, source, name, id, type)
        if source and tuple not in _to_translate:
            _to_translate.append(tuple)

    def encode(s):
        if isinstance(s, unicode):
            return s.encode('utf8')
        return s

    for (xml_name,model,res_id,module) in cr.fetchall():
        module = encode(module)
        model = encode(model)
        xml_name = "%s.%s" % (module, encode(xml_name))

        if not pool.get(model):
            _logger.error("Unable to find object %r", model)
            continue

        exists = pool.get(model).exists(cr, uid, res_id)
        if not exists:
            _logger.warning("Unable to find object %r with id %d", model, res_id)
            continue
        obj = pool.get(model).browse(cr, uid, res_id)

        if model=='ir.ui.view':
            d = etree.XML(encode(obj.arch))
            for t in trans_parse_view(d):
                push_translation(module, 'view', encode(obj.model), 0, t)
        elif model=='ir.actions.wizard':
            service_name = 'wizard.'+encode(obj.wiz_name)
            import openerp.netsvc as netsvc
            if netsvc.Service._services.get(service_name):
                obj2 = netsvc.Service._services[service_name]
                for state_name, state_def in obj2.states.iteritems():
                    if 'result' in state_def:
                        result = state_def['result']
                        if result['type'] != 'form':
                            continue
                        name = "%s,%s" % (encode(obj.wiz_name), state_name)

                        def_params = {
                            'string': ('wizard_field', lambda s: [encode(s)]),
                            'selection': ('selection', lambda s: [encode(e[1]) for e in ((not callable(s)) and s or [])]),
                            'help': ('help', lambda s: [encode(s)]),
                        }

                        # export fields
                        if not result.has_key('fields'):
                            _logger.warning("res has no fields: %r", result)
                            continue
                        for field_name, field_def in result['fields'].iteritems():
                            res_name = name + ',' + field_name

                            for fn in def_params:
                                if fn in field_def:
                                    transtype, modifier = def_params[fn]
                                    for val in modifier(field_def[fn]):
                                        push_translation(module, transtype, res_name, 0, val)

                        # export arch
                        arch = result['arch']
                        if arch and not isinstance(arch, UpdateableStr):
                            d = etree.XML(arch)
                            for t in trans_parse_view(d):
                                push_translation(module, 'wizard_view', name, 0, t)

                        # export button labels
                        for but_args in result['state']:
                            button_name = but_args[0]
                            button_label = but_args[1]
                            res_name = name + ',' + button_name
                            push_translation(module, 'wizard_button', res_name, 0, button_label)

        elif model=='ir.model.fields':
            try:
                field_name = encode(obj.name)
            except AttributeError, exc:
                _logger.error("name error in %s: %s", xml_name, str(exc))
                continue
            objmodel = pool.get(obj.model)
            if not objmodel or not field_name in objmodel._columns:
                continue
            field_def = objmodel._columns[field_name]

            name = "%s,%s" % (encode(obj.model), field_name)
            push_translation(module, 'field', name, 0, encode(field_def.string))

            if field_def.help:
                push_translation(module, 'help', name, 0, encode(field_def.help))

            if field_def.translate:
                ids = objmodel.search(cr, uid, [])
                obj_values = objmodel.read(cr, uid, ids, [field_name])
                for obj_value in obj_values:
                    res_id = obj_value['id']
                    if obj.name in ('ir.model', 'ir.ui.menu'):
                        res_id = 0
                    model_data_ids = model_data_obj.search(cr, uid, [
                        ('model', '=', model),
                        ('res_id', '=', res_id),
                        ])
                    if not model_data_ids:
                        push_translation(module, 'model', name, 0, encode(obj_value[field_name]))

            if hasattr(field_def, 'selection') and isinstance(field_def.selection, (list, tuple)):
                for dummy, val in field_def.selection:
                    push_translation(module, 'selection', name, 0, encode(val))

        elif model=='ir.actions.report.xml':
            name = encode(obj.report_name)
            fname = ""
            if obj.report_rml:
                fname = obj.report_rml
                parse_func = trans_parse_rml
                report_type = "report"
            elif obj.report_xsl:
                fname = obj.report_xsl
                parse_func = trans_parse_xsl
                report_type = "xsl"
            if fname and obj.report_type in ('pdf', 'xsl'):
                try:
                    report_file = misc.file_open(fname)
                    try:
                        d = etree.parse(report_file)
                        for t in parse_func(d.iter()):
                            push_translation(module, report_type, name, 0, t)
                    finally:
                        report_file.close()
                except (IOError, etree.XMLSyntaxError):
                    _logger.exception("couldn't export translation for report %s %s %s", name, report_type, fname)

        for field_name,field_def in obj._table._columns.items():
            if field_def.translate:
                name = model + "," + field_name
                try:
                    trad = getattr(obj, field_name) or ''
                except:
                    trad = ''
                push_translation(module, 'model', name, xml_name, encode(trad))

        # End of data for ir.model.data query results

    cr.execute(query_models, query_param)

    def push_constraint_msg(module, term_type, model, msg):
        # Check presence of __call__ directly instead of using
        # callable() because it will be deprecated as of Python 3.0
        if not hasattr(msg, '__call__'):
            push_translation(module, term_type, model, 0, encode(msg))

    for (model_id, model, module) in cr.fetchall():
        module = encode(module)
        model = encode(model)

        model_obj = pool.get(model)

        if not model_obj:
            _logger.error("Unable to find object %r", model)
            continue

        for constraint in getattr(model_obj, '_constraints', []):
            push_constraint_msg(module, 'constraint', model, constraint[1])

        for constraint in getattr(model_obj, '_sql_constraints', []):
            push_constraint_msg(module, 'sql_constraint', model, constraint[2])

    # parse source code for _() calls
    def get_module_from_path(path, mod_paths=None):
        if not mod_paths:
            # First, construct a list of possible paths
            def_path = os.path.abspath(os.path.join(config.config['root_path'], 'addons'))     # default addons path (base)
            ad_paths= map(lambda m: os.path.abspath(m.strip()),config.config['addons_path'].split(','))
            mod_paths=[def_path]
            for adp in ad_paths:
                mod_paths.append(adp)
                if not os.path.isabs(adp):
                    mod_paths.append(adp)
                elif adp.startswith(def_path):
                    mod_paths.append(adp[len(def_path)+1:])
        for mp in mod_paths:
            if path.startswith(mp) and (os.path.dirname(path) != mp):
                path = path[len(mp)+1:]
                return path.split(os.path.sep)[0]
        return 'base'   # files that are not in a module are considered as being in 'base' module

    modobj = pool.get('ir.module.module')
    installed_modids = modobj.search(cr, uid, [('state', '=', 'installed')])
    installed_modules = map(lambda m: m['name'], modobj.read(cr, uid, installed_modids, ['name']))

    root_path = os.path.join(config.config['root_path'], 'addons')

    apaths = map(os.path.abspath, map(str.strip, config.config['addons_path'].split(',')))
    if root_path in apaths:
        path_list = apaths
    else :
        path_list = [root_path,] + apaths

    # Also scan these non-addon paths
    for bin_path in ['osv', 'report' ]:
        path_list.append(os.path.join(config.config['root_path'], bin_path))

    _logger.debug("Scanning modules at paths: ", path_list)

    mod_paths = []
    join_dquotes = re.compile(r'([^\\])"[\s\\]*"', re.DOTALL)
    join_quotes = re.compile(r'([^\\])\'[\s\\]*\'', re.DOTALL)
    re_dquotes = re.compile(r'[^a-zA-Z0-9_]_\([\s]*"(.+?)"[\s]*?\)', re.DOTALL)
    re_quotes = re.compile(r'[^a-zA-Z0-9_]_\([\s]*\'(.+?)\'[\s]*?\)', re.DOTALL)

    def export_code_terms_from_file(fname, path, root, terms_type):
        fabsolutepath = join(root, fname)
        frelativepath = fabsolutepath[len(path):]
        module = get_module_from_path(fabsolutepath, mod_paths=mod_paths)
        is_mod_installed = module in installed_modules
        if (('all' in modules) or (module in modules)) and is_mod_installed:
            _logger.debug("Scanning code of %s at module: %s", frelativepath, module)
            src_file = misc.file_open(fabsolutepath, subdir='')
            try:
                code_string = src_file.read()
            finally:
                src_file.close()
            if module in installed_modules:
                frelativepath = str("addons" + frelativepath)
            ite = re_dquotes.finditer(code_string)
            code_offset = 0
            code_line = 1
            for i in ite:
                src = i.group(1)
                if src.startswith('""'):
                    assert src.endswith('""'), "Incorrect usage of _(..) function (should contain only literal strings!) in file %s near: %s" % (frelativepath, src[:30])
                    src = src[2:-2]
                else:
                    src = join_dquotes.sub(r'\1', src)
                # try to count the lines from the last pos to our place:
                code_line += code_string[code_offset:i.start(1)].count('\n')
                # now, since we did a binary read of a python source file, we
                # have to expand pythonic escapes like the interpreter does.
                src = src.decode('string_escape')
                push_translation(module, terms_type, frelativepath, code_line, encode(src))
                code_line += i.group(1).count('\n')
                code_offset = i.end() # we have counted newlines up to the match end

            ite = re_quotes.finditer(code_string)
            code_offset = 0 #reset counters
            code_line = 1
            for i in ite:
                src = i.group(1)
                if src.startswith("''"):
                    assert src.endswith("''"), "Incorrect usage of _(..) function (should contain only literal strings!) in file %s near: %s" % (frelativepath, src[:30])
                    src = src[2:-2]
                else:
                    src = join_quotes.sub(r'\1', src)
                code_line += code_string[code_offset:i.start(1)].count('\n')
                src = src.decode('string_escape')
                push_translation(module, terms_type, frelativepath, code_line, encode(src))
                code_line += i.group(1).count('\n')
                code_offset = i.end() # we have counted newlines up to the match end

    for path in path_list:
        _logger.debug("Scanning files of modules at %s", path)
        for root, dummy, files in osutil.walksymlinks(path):
            for fname in itertools.chain(fnmatch.filter(files, '*.py')):
                export_code_terms_from_file(fname, path, root, 'code')
            for fname in itertools.chain(fnmatch.filter(files, '*.mako')):
                export_code_terms_from_file(fname, path, root, 'report')


    out = [["module","type","name","res_id","src","value"]] # header
    _to_translate.sort()
    # translate strings marked as to be translated
    for module, source, name, id, type in _to_translate:
        trans = trans_obj._get_source(cr, uid, name, type, lang, source)
        out.append([module, type, name, id, source, encode(trans) or ''])

    return out

def trans_load(cr, filename, lang, verbose=True, flag=None, module_name=None, context=None):
    try:
        fileobj = misc.file_open(filename)
        pool = pooler.get_pool(cr.dbname)
        traslation_obj = pool.get('ir.translation')
        _logger.info("loading %s", filename)
        if flag == 'web':
            transl = {"messages":[]}
            po = babel.messages.pofile.read_po(fileobj)
            for x in po:
                if x.id and x.string and "openerp-web" in x.auto_comments:
                    transl["messages"].append({'id': x.id, 'string': x.string})
            return transl
        else:
            fileformat = os.path.splitext(filename)[-1][1:].lower()
            r = trans_load_data(cr, fileobj, fileformat, lang, verbose=verbose, module_name=module_name, context=context)
        fileobj.close()
        return r
    except IOError:
        if verbose:
            _logger.error("couldn't read translation file %s", filename)
        return None

def trans_load_data(cr, fileobj, fileformat, lang, lang_name=None, verbose=True, module_name=None, context=None):
    """Populates the ir_translation table."""
    if verbose:
        _logger.info('loading translation file for language %s', lang)
    if context is None:
        context = {}
    db_name = cr.dbname
    pool = pooler.get_pool(db_name)
    lang_obj = pool.get('res.lang')
    trans_obj = pool.get('ir.translation')
    iso_lang = misc.get_iso_codes(lang)
    try:
        uid = 1
        ids = lang_obj.search(cr, uid, [('code','=', lang)])

        if not ids:
            # lets create the language with locale information
            lang_obj.load_lang(cr, 1, lang=lang, lang_name=lang_name)


        # now, the serious things: we read the language file
        fileobj.seek(0)
        if fileformat == 'csv':
            reader = csv.reader(fileobj, quotechar='"', delimiter=',')
            # read the first line of the file (it contains columns titles)
            for row in reader:
                f = row
                break
        elif fileformat == 'po':
            reader = TinyPoFile(fileobj)
            f = ['type', 'name', 'res_id', 'src', 'value', 'module']
        else:
            _logger.error('Bad file format: %s', fileformat)
            raise Exception(_('Bad file format'))

        # read the rest of the file
        line = 1
        irt_cursor = trans_obj._get_import_cursor(cr, uid, context=context)

        for row in reader:
            line += 1
            # skip empty rows and rows where the translation field (=last fiefd) is empty
            #if (not row) or (not row[-1]):
            #    continue

            # dictionary which holds values for this line of the csv file
            # {'lang': ..., 'type': ..., 'name': ..., 'res_id': ...,
            #  'src': ..., 'value': ...}
            dic = {'lang': lang}
            dic_module = False
            for i in range(len(f)):
                if f[i] in ('module',):
                    continue
                dic[f[i]] = row[i]

            # This would skip terms that fail to specify a res_id
            if not dic.get('res_id', False):
                continue

            res_id = dic.pop('res_id')
            if res_id and isinstance(res_id, (int, long)) \
                or (isinstance(res_id, basestring) and res_id.isdigit()):
                    dic['res_id'] = int(res_id)
                    dic['module'] = module_name
            else:
                try:
                    tmodel = dic['name'].split(',')[0]
                    if '.' in res_id:
                        tmodule, tname = res_id.split('.', 1)
                    else:
                        tmodule = dic_module
                        tname = res_id
                    dic['imd_model'] = tmodel
                    dic['module'] = tmodule
                    dic['imd_name'] =  tname
                    dic['res_id'] = None
                except Exception:
                    _logger.warning("Could not decode resource for %s, please fix the po file.",
                                    dic['res_id'], exc_info=True)
                    dic['res_id'] = None

            irt_cursor.push(dic)

        irt_cursor.finish()
        if verbose:
            _logger.info("translation file loaded succesfully")
    except IOError:
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
    """Loads a translation terms for a language.
    Used mainly to automate language loading at db initialization.

    :param lang: language ISO code with optional _underscore_ and l10n flavor (ex: 'fr', 'fr_BE', but not 'fr-BE')
    :type lang: str
    """
    pool = pooler.get_pool(cr.dbname)
    language_installer = pool.get('base.language.install')
    uid = 1
    oid = language_installer.create(cr, uid, {'lang': lang})
    language_installer.lang_install(cr, uid, [oid], context=None)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

