# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from interface import  report_rml
import StringIO
import base64
import copy
import ir
import locale
import mx.DateTime
import netsvc
import os
import osv
import pooler
import re
import time
import tools
import warnings
import xml.dom.minidom
import zipfile

DT_FORMAT = '%Y-%m-%d'
DHM_FORMAT = '%Y-%m-%d %H:%M:%S'
HM_FORMAT = '%H:%M:%S'

if not hasattr(locale, 'nl_langinfo'):
    locale.nl_langinfo = lambda *a: '%x'

if not hasattr(locale, 'D_FMT'):
    locale.D_FMT = None

rml_parents = {
    'tr':1,
    'li':1,
    'story': 0,
    'section': 0
}

rml_tag="para"

sxw_parents = {
    'table-row': 1,
    'list-item': 1,
    'body': 0,
    'section': 0,
}

sxw_tag = "p"

rml2sxw = {
    'para': 'p',
}

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
    'es_ES': 'Spanish_Spain',
    'sv_SE': 'Swedish_Sweden',
    'ta_IN': 'English_Australia',
    'th_TH': 'Thai_Thailand',
    'mi_NZ': 'Maori',
    'tr_TR': 'Turkish_Turkey',
    'uk_UA': 'Ukrainian_Ukraine',
    'vi_VN': 'Vietnamese_Viet Nam',
}

class _format(object):
    def set_value(self, name, object, field):
        #super(_date_format, self).__init__(self)
        self.object = object
        self._field = field
        self.name=name
        lc, encoding = locale.getdefaultlocale()
        if not encoding:
            encoding = 'UTF-8'
        if encoding == 'utf':
            encoding = 'UTF-8'
        if encoding == 'cp1252':
            encoding= '1252'
        lang = self.object._context.get('lang', 'en_US') or 'en_US'
        try:
            if os.name == 'nt':
                locale.setlocale(locale.LC_ALL, _LOCALE2WIN32.get(lang, lang) + '.' + encoding)
            else:
                locale.setlocale(locale.LC_ALL,str( lang + '.' + encoding))
        except Exception:
            netsvc.Logger().notifyChannel('report', netsvc.LOG_WARNING,
                    'report %s: unable to set locale "%s"' % (self.name,
                        self.object._context.get('lang', 'en_US') or 'en_US'))


class _float_format(float, _format):
    def __str__(self):
        if not self.object._context:
            return locale.format('%f', self.name, True)
        digit = 2
        if hasattr(self._field, 'digits') and self._field.digits:
            digit = self._field.digits[1]
        return locale.format('%.' + str(digit) + 'f', self.name, True)


class _int_format(int, _format):
    def __str__(self):
        return locale.format('%d', self.name, True)


class _date_format(str, _format):
    def __str__(self):
        if not self.object._context:
            return self.name

        if self.name:
            try :
                datedata = time.strptime(self.name, DT_FORMAT)
                return time.strftime(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'),
                    datedata)
            except :
                pass
        return ''


_fields_process = {
    'float': _float_format,
    'date': _date_format,
    'integer': _int_format
}

#
# Context: {'node': node.dom}
#
class browse_record_list(list):
    def __init__(self, lst, context):
        super(browse_record_list, self).__init__(lst)
        self.context = context

    def __getattr__(self, name):
        res = browse_record_list([getattr(x,name) for x in self], self.context)
        return res

    def __str__(self):
        return "browse_record_list("+str(len(self))+")"

    def repeatIn(self, name):
        warnings.warn('Use repeatIn(object_list, \'variable\')', DeprecationWarning)
        node = self.context['_node']
        parents = self.context.get('parents', rml_parents)
        node.data = ''
        while True:
            if not node.parentNode:
                break
            node = node.parentNode
            if node.nodeType == node.ELEMENT_NODE and node.localName in parents:
                break
        parent_node = node
        if not len(self):
            return None
        nodes = [(0,node)]
        for i in range(1,len(self)):
            newnode = parent_node.cloneNode(1)
            n = parent_node.parentNode
            n.insertBefore(newnode, parent_node)
            nodes.append((i,newnode))
        for i,node in nodes:
            self.context[name] = self[i]
            self.context['_self']._parse_node(node)
        return None

class rml_parse(object):
    def __init__(self, cr, uid, name, parents=rml_parents, tag=rml_tag, context=None):
        if not context:
            context={}
        self.cr = cr
        self.uid = uid
        self.pool = pooler.get_pool(cr.dbname)
        user = self.pool.get('res.users').browse(cr, uid, uid, fields_process=_fields_process)
        self.localcontext = {
            'user': user,
            'company': user.company_id,
            'repeatIn': self.repeatIn,
            'setLang': self.setLang,
            'setTag': self.setTag,
            'removeParentNode': self.removeParentNode,
            'format': self.format,
            'formatLang': self.formatLang,
            'logo' : user.company_id.logo,
            'lang' : user.company_id.partner_id.lang,
        }
        self.localcontext.update(context)
        self.rml_header = user.company_id.rml_header
        self.rml_header2 = user.company_id.rml_header2
        self.logo = user.company_id.logo
        self.name = name
        self._regex = re.compile('\[\[(.+?)\]\]')
        self._transl_regex = re.compile('(\[\[.+?\]\])')
        self._node = None
        self.parents = parents
        self.tag = tag
        self._lang_cache = {}
#       self.already = {}

    def setTag(self, oldtag, newtag, attrs=None):
        if not attrs:
            attrs={}
        node = self._find_parent(self._node, [oldtag])
        if node:
            node.tagName = newtag
            for key, val in attrs.items():
                node.setAttribute(key, val)
        return None

    def format(self, text, oldtag=None):
        if not oldtag:
            oldtag = self.tag
        self._node.data = ''
        node = self._find_parent(self._node, [oldtag])
        ns = None
        if node:
            pp = node.parentNode
            ns = node.nextSibling
            pp.removeChild(node)
            self._node = pp
            
        lst = tools.ustr(text).split('\n')
        if not (text and lst):
            return None
        nodes = []
        for i in range(len(lst)):
            newnode = node.cloneNode(1)
            newnode.tagName=rml_tag
            newnode.childNodes[0].data = lst[i]
            if ns:
                pp.insertBefore(newnode, ns)
            else:
                pp.appendChild(newnode)
            nodes.append((i, newnode))

    def removeParentNode(self, tag=None):
        if not tag:
            tag = self.tag
        if self.tag == sxw_tag and rml2sxw.get(tag, False):
            tag = rml2sxw[tag]
        node = self._find_parent(self._node, [tag])
        if node:
            parentNode = node.parentNode
            parentNode.removeChild(node)
            self._node = parentNode

    def setLang(self, lang):
        self.localcontext['lang'] = lang
        for obj in self.objects:
            obj._context['lang'] = lang
            for table in obj._cache:
                for id in obj._cache[table]:
                    self._lang_cache.setdefault(obj._context['lang'], {}).setdefault(table,
                            {}).update(obj._cache[table][id])
                    if lang in self._lang_cache \
                            and table in self._lang_cache[lang] \
                            and id in self._lang_cache[lang][table]:
                        obj._cache[table][id] = self._lang_cache[lang][table][id]
                    else:
                        obj._cache[table][id] = {'id': id}


    def formatLang(self, value, digits=2, date=False,date_time=False, grouping=True, monetary=False, currency=None):
        if isinstance(value, (str, unicode)) and not value:
            return ''
        pool_lang=self.pool.get('res.lang')
        lang = self.localcontext.get('lang', 'en_US') or 'en_US'
        lang_obj = pool_lang.browse(self.cr,self.uid,pool_lang.search(self.cr,self.uid,[('code','=',lang)])[0])
        if date or date_time:
            date_format = lang_obj.date_format
            if date_time:
                date_format = lang_obj.date_format + " " + lang_obj.time_format
            if not isinstance(value, time.struct_time):
                # assume string, parse it
                if len(str(value)) == 10:
                    # length of date like 2001-01-01 is ten
                    # assume format '%Y-%m-%d'
                    date = mx.DateTime.strptime(value,DT_FORMAT)
                else:
                    # assume format '%Y-%m-%d %H:%M:%S'
                    value = str(value)[:19]
                    date = mx.DateTime.strptime(str(value),DHM_FORMAT)
            else:
                date = mx.DateTime.DateTime(*(value.timetuple()[:6]))
            return date.strftime(date_format)
        return lang_obj.format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)
    
#    def formatLang(self, value, digit=2, date=False):
#        if not value:
#            return ''
#        lc, encoding = locale.getdefaultlocale()
#        if not encoding:
#            encoding = 'UTF-8'
#        if encoding == 'utf':
#            encoding = 'UTF-8'
#        if encoding == 'cp1252':
#            encoding= '1252'
#        lang = self.localcontext.get('lang', 'en_US') or 'en_US'
#        try:
#            if os.name == 'nt':
#                locale.setlocale(locale.LC_ALL, _LOCALE2WIN32.get(lang, lang) + '.' + encoding)
#            else:
#                locale.setlocale(locale.LC_ALL, lang + '.' + encoding)
#        except Exception:
#            netsvc.Logger().notifyChannel('report', netsvc.LOG_WARNING,
#                    'report %s: unable to set locale "%s"' % (self.name,
#                        self.localcontext.get('lang', 'en_US') or 'en_US'))
#        if date:
#            date = time.strptime(value, DT_FORMAT)
#            return time.strftime(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'),
#                    date)
#        return locale.format('%.' + str(digit) + 'f', value, True)

    def repeatIn(self, lst, name, nodes_parent=False):
        self._node.data = ''
        node = self._find_parent(self._node, nodes_parent or self.parents)

        pp = node.parentNode
        ns = node.nextSibling
        pp.removeChild(node)
        self._node = pp

        if not len(lst):
            return None
        nodes = []
        for i in range(len(lst)):
            newnode = node.cloneNode(1)
            if ns:
                pp.insertBefore(newnode, ns)
            else:
                pp.appendChild(newnode)
            nodes.append((i, newnode))
        for i, node in nodes:
            self.node_context[node] = {name: lst[i]}
        return None

    def _eval(self, expr):
        try:
            res = eval(expr, self.localcontext)
            if (res is None) or (res=='') or (res is False):
                res = ''
        except Exception,e:
            import traceback, sys
            tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
            netsvc.Logger().notifyChannel('report', netsvc.LOG_ERROR,
                    'report %s:\n%s\n%s\nexpr: %s' % (self.name, tb_s, str(e),
                        expr.encode('utf-8')))
            res = ''
        return res

    def _find_parent(self, node, parents):
        while True:
            if not node.parentNode:
                return False
            node = node.parentNode
            if node.nodeType == node.ELEMENT_NODE and node.localName in parents:
                break
        return node

    def _parse_text(self, text, level=None):
        if not level:
            level=[]
        res = self._regex.findall(text)
        todo = []
        # translate the text
        # the "split [[]] if not match [[]]" is not very nice, but I
        # don't see how I could do it better...
        # what I'd like to do is a re.sub(NOT pattern, func, string)
        # but I don't know how to do that...
        # translate the RML file
        if 'lang' in self.localcontext:
            lang = self.localcontext['lang']
            if lang and text and not text.isspace():
                transl_obj = self.pool.get('ir.translation')
                piece_list = self._transl_regex.split(text)
                for pn in range(len(piece_list)):
                    if not self._transl_regex.match(piece_list[pn]):
                        source_string = piece_list[pn].replace('\n', ' ').strip()
                        if len(source_string):
                            translated_string = transl_obj._get_source(self.cr, self.uid, self.name, 'rml', lang, source_string)
                            if translated_string:
                                piece_list[pn] = piece_list[pn].replace(source_string, translated_string)
                text = ''.join(piece_list)
        for key in res:
            newtext = self._eval(key)
            for i in range(len(level)):
                if isinstance(newtext, list):
                    newtext = newtext[level[i]]
            if isinstance(newtext, list):
                todo.append((key, newtext))
            else:
                # if there are two [[]] blocks the same, it will replace both
                # but it's ok because it should evaluate to the same thing
                # anyway
                newtext = tools.ustr(newtext)
                text = text.replace('[['+key+']]', newtext)
        self._node.data = text
        if len(todo):
            for key, newtext in todo:
                parent_node = self._find_parent(self._node, parents)
                assert parents.get(parent_node.localName, False), 'No parent node found !'
                nodes = [parent_node]
                for i in range(len(newtext) - 1):
                    newnode = parent_node.cloneNode(1)
                    if parents.get(parent_node.localName, False):
                        n = parent_node.parentNode
                        parent_node.parentNode.insertAfter(newnode, parent_node)
                        nodes.append(newnode)
            return False
        return text

    def _parse_node(self):
        level = []
        while True:
            if self._node.nodeType==self._node.ELEMENT_NODE:
                if self._node.hasAttribute('expr'):
                    newattrs = self._eval(self._node.getAttribute('expr'))
                    for key,val in newattrs.items():
                        self._node.setAttribute(key,val)

            if self._node.hasChildNodes():
                self._node = self._node.firstChild
            elif self._node.nextSibling:
                self._node = self._node.nextSibling
            else:
                while self._node and not self._node.nextSibling:
                    self._node = self._node.parentNode
                if not self._node:
                    break
                self._node = self._node.nextSibling
            if self._node in self.node_context:
                self.localcontext.update(self.node_context[self._node])
            if self._node.nodeType in (self._node.CDATA_SECTION_NODE, self._node.TEXT_NODE):
#               if self._node in self.already:
#                   self.already[self._node] += 1
#                   print "second pass!", self.already[self._node], '---%s---' % self._node.data
#               else:
#                   self.already[self._node] = 0
                self._parse_text(self._node.data, level)
        return True

    def _find_node(self, node, localname):
        if node.localName==localname:
            return node
        for tag in node.childNodes:
            if tag.nodeType==tag.ELEMENT_NODE:
                found = self._find_node(tag, localname)
                if found:
                    return found
        return False

    def _add_header(self, node, header=1):
        if header==2:
            rml_head =  self.rml_header2
        else:
            rml_head =  self.rml_header

        # Refactor this patch, to use the minidom interface
        if self.logo and (rml_head.find('company.logo')<0 or rml_head.find('<image')<0) and rml_head.find('<!--image')<0:
            rml_head =  rml_head.replace('<pageGraphics>','''<pageGraphics> <image x="10" y="26cm" height="70" width="90" >[[company.logo]] </image> ''')
        if not self.logo and rml_head.find('company.logo')>=0:
            rml_head = rml_head.replace('<image','<!--image')
            rml_head = rml_head.replace('</image>','</image-->')

        head_dom = xml.dom.minidom.parseString(rml_head)
        #for frame in head_dom.getElementsByTagName('frame'):
        #   frame.parentNode.removeChild(frame)
        node2 = head_dom.documentElement
        for tag in node2.childNodes:
            if tag.nodeType==tag.ELEMENT_NODE:
                found = self._find_node(node, tag.localName)
        #       rml_frames = found.getElementsByTagName('frame')
                if found:
                    if tag.hasAttribute('position') and (tag.getAttribute('position')=='inside'):
                        found.appendChild(tag)
                    else:
                        found.parentNode.replaceChild(tag, found)
        #       for frame in rml_frames:
        #           tag.appendChild(frame)
        return True

    def preprocess(self, objects, data, ids):
        self.localcontext['data'] = data
        self.localcontext['objects'] = objects
        self.datas = data
        self.ids = ids
        self.objects = objects

    def _parse(self, rml_dom, objects, data, header=0):
        self.node_context = {}
        self.dom = rml_dom
        self._node = self.dom.documentElement
        if header:
            self._add_header(self._node, header)
        self._parse_node()
        res = self.dom.documentElement.toxml('utf-8')
        return res

class report_sxw(report_rml):
    def __init__(self, name, table, rml, parser=rml_parse, header=True, store=False):
        report_rml.__init__(self, name, table, rml, '')
        self.name = name
        self.parser = parser
        self.header = header
        self.store = store

    def getObjects(self, cr, uid, ids, context):
        table_obj = pooler.get_pool(cr.dbname).get(self.table)
        return table_obj.browse(cr, uid, ids, list_class=browse_record_list, context=context,
            fields_process=_fields_process)

    def create(self, cr, uid, ids, data, context=None):
        if not context:
            context={}
        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cr, uid,
                [('report_name', '=', self.name[7:])], context=context)

        if report_xml_ids:
            report_xml = ir_obj.browse(cr, uid, report_xml_ids[0],
                    context=context)
            attach = report_xml.attachment
        else:
            ir_menu_report_obj = pool.get('ir.ui.menu')
            report_menu_ids = ir_menu_report_obj.search(cr, uid,
                    [('id', 'in', ids)], context=context)
            title = ''
            if report_menu_ids:
                report_name = ir_menu_report_obj.browse(cr, uid, report_menu_ids[0],
                    context=context)
                title = report_name.name
            rml = tools.file_open(self.tmpl, subdir=None).read()
            report_type= data.get('report_type', 'pdf')
            class a(object):
                def __init__(self, *args, **argv):
                    for key,arg in argv.items():
                        setattr(self, key, arg)
            report_xml = a(title=title, report_type=report_type, report_rml_content=rml, name=title, attachment=False, header=self.header)
            attach = False

        if attach:
            objs = self.getObjects(cr, uid, ids, context)
            results = []
            for obj in objs:
                aname = eval(attach, {'object':obj, 'time':time})
                result = False
                if report_xml.attachment_use and aname and context.get('attachment_use', True):
                    aids = pool.get('ir.attachment').search(cr, uid, [('datas_fname','=',aname+'.pdf'),('res_model','=',self.table),('res_id','=',obj.id)])
                    if aids:
                        d = base64.decodestring(pool.get('ir.attachment').browse(cr, uid, aids[0]).datas)
                        results.append((d,'pdf'))
                        continue

                result = self.create_single(cr, uid, [obj.id], data, report_xml, context)
                if aname:
                    name = aname+'.'+result[1]
                    pool.get('ir.attachment').create(cr, uid, {
                        'name': aname,
                        'datas': base64.encodestring(result[0]),
                        'datas_fname': name,
                        'res_model': self.table,
                        'res_id': obj.id,
                        }, context=context
                    )
                    cr.commit()
                results.append(result)

            if results[0][1]=='pdf':
                from pyPdf import PdfFileWriter, PdfFileReader
                import cStringIO
                output = PdfFileWriter()
                for r in results:
                    reader = PdfFileReader(cStringIO.StringIO(r[0]))
                    for page in range(reader.getNumPages()):
                        output.addPage(reader.getPage(page))
                s = cStringIO.StringIO()
                output.write(s)
                return s.getvalue(), results[0][1]
        return self.create_single(cr, uid, ids, data, report_xml, context)

    def create_single(self, cr, uid, ids, data, report_xml, context={}):
        logo = None
        context = context.copy()
        pool = pooler.get_pool(cr.dbname)
        want_header = self.header
        title = report_xml.name
        attach = report_xml.attachment
        report_type = report_xml.report_type
        want_header = report_xml.header

        if report_type in ['sxw','odt']:
            context['parents'] = sxw_parents
            sxw_io = StringIO.StringIO(report_xml.report_sxw_content)
            sxw_z = zipfile.ZipFile(sxw_io, mode='r')
            rml = sxw_z.read('content.xml')
            meta = sxw_z.read('meta.xml')
            sxw_z.close()
            rml_parser = self.parser(cr, uid, self.name2, context)
            rml_parser.parents = sxw_parents
            rml_parser.tag = sxw_tag
            objs = self.getObjects(cr, uid, ids, context)
            rml_parser.preprocess(objs, data, ids)
            rml_dom = xml.dom.minidom.parseString(rml)

            node = rml_dom.documentElement

            elements = node.getElementsByTagName("text:p")

            for pe in elements:
                e = pe.getElementsByTagName("text:drop-down")
                for de in e:
                    pp=de.parentNode
                    for cnd in de.childNodes:
                        if cnd.nodeType in (cnd.CDATA_SECTION_NODE, cnd.TEXT_NODE):
                            pe.appendChild(cnd)
                            pp.removeChild(de)

            # Add Information : Resource ID and Model
            rml_dom_meta = xml.dom.minidom.parseString(meta)
            node = rml_dom_meta.documentElement
            elements = node.getElementsByTagName("meta:user-defined")
            for pe in elements:
                if pe.hasAttribute("meta:name"):
                    if pe.getAttribute("meta:name") == "Info 3":
                        pe.childNodes[0].data=data['id']
                    if pe.getAttribute("meta:name") == "Info 4":
                        pe.childNodes[0].data=data['model']
            meta = rml_dom_meta.documentElement.toxml('utf-8')

            rml2 = rml_parser._parse(rml_dom, objs, data, header=want_header)
            sxw_z = zipfile.ZipFile(sxw_io, mode='a')
            sxw_z.writestr('content.xml', "<?xml version='1.0' encoding='UTF-8'?>" + \
                    rml2)
            sxw_z.writestr('meta.xml', "<?xml version='1.0' encoding='UTF-8'?>" + \
                    meta)

            if want_header:
                #Add corporate header/footer
                if report_type=='odt':
                    rml = tools.file_open('custom/corporate_odt_header.xml').read()
                if report_type=='sxw':
                    rml = tools.file_open('custom/corporate_sxw_header.xml').read()
                rml_parser = self.parser(cr, uid, self.name2, context)
                rml_parser.parents = sxw_parents
                rml_parser.tag = sxw_tag
                objs = self.getObjects(cr, uid, ids, context)
                rml_parser.preprocess(objs, data, ids)
                rml_dom = xml.dom.minidom.parseString(rml)
                rml2 = rml_parser._parse(rml_dom, objs, data, header=want_header)
                sxw_z.writestr('styles.xml',"<?xml version='1.0' encoding='UTF-8'?>" + \
                        rml2)
            sxw_z.close()
            rml2 = sxw_io.getvalue()
            sxw_io.close()
        else:
            rml = report_xml.report_rml_content
            context['parents'] = rml_parents
            rml_parser = self.parser(cr, uid, self.name2, context)
            rml_parser.parents = rml_parents
            rml_parser.tag = rml_tag
            objs = self.getObjects(cr, uid, ids, context)
            rml_parser.preprocess(objs, data, ids)
            rml_dom = xml.dom.minidom.parseString(rml)
            rml2 = rml_parser._parse(rml_dom, objs, data, header=want_header)
            if rml_parser.logo:
                logo = base64.decodestring(rml_parser.logo)

        create_doc = self.generators[report_type]
        pdf = create_doc(rml2, logo, title.encode('utf8'))

        return (pdf, report_type)

