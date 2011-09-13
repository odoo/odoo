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
from lxml import etree
import StringIO
import cStringIO
import base64
from datetime import datetime
import os
import re
import time
from interface import report_rml
import preprocess
import logging
import openerp.pooler as pooler
import openerp.tools as tools
import zipfile
import common
from openerp.osv.fields import float as float_class, function as function_class
from openerp.osv.orm import browse_record
from openerp.tools.translate import _

DT_FORMAT = '%Y-%m-%d'
DHM_FORMAT = '%Y-%m-%d %H:%M:%S'
HM_FORMAT = '%H:%M:%S'

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

html_parents = {
    'tr' : 1,
    'body' : 0,
    'div' : 0
    }
sxw_tag = "p"

rml2sxw = {
    'para': 'p',
}

class _format(object):
    def set_value(self, cr, uid, name, object, field, lang_obj):
        self.object = object
        self._field = field
        self.name = name
        self.lang_obj = lang_obj

class _float_format(float, _format):
    def __init__(self,value):
        super(_float_format, self).__init__()
        self.val = value

    def __str__(self):
        digits = 2
        if hasattr(self,'_field') and getattr(self._field, 'digits', None):
            digits = self._field.digits[1]
        if hasattr(self, 'lang_obj'):
            return self.lang_obj.format('%.' + str(digits) + 'f', self.name, True)
        return self.val

class _int_format(int, _format):
    def __init__(self,value):
        super(_int_format, self).__init__()
        self.val = value and str(value) or str(0)

    def __str__(self):
        if hasattr(self,'lang_obj'):
            return self.lang_obj.format('%.d', self.name, True)
        return self.val

class _date_format(str, _format):
    def __init__(self,value):
        super(_date_format, self).__init__()
        self.val = value and str(value) or ''

    def __str__(self):
        if self.val:
            if getattr(self,'name', None):
                date = datetime.strptime(self.name, DT_FORMAT)
                return date.strftime(str(self.lang_obj.date_format))
        return self.val

class _dttime_format(str, _format):
    def __init__(self,value):
        super(_dttime_format, self).__init__()
        self.val = value and str(value) or ''

    def __str__(self):
        if self.val and getattr(self,'name', None):
            return datetime.strptime(self.name, DHM_FORMAT)\
                   .strftime("%s %s"%(str(self.lang_obj.date_format),
                                      str(self.lang_obj.time_format)))
        return self.val


_fields_process = {
    'float': _float_format,
    'date': _date_format,
    'integer': _int_format,
    'datetime' : _dttime_format
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

class rml_parse(object):
    def __init__(self, cr, uid, name, parents=rml_parents, tag=rml_tag, context=None):
        if not context:
            context={}
        self.cr = cr
        self.uid = uid
        self.pool = pooler.get_pool(cr.dbname)
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        self.localcontext = {
            'user': user,
            'setCompany': self.setCompany,
            'repeatIn': self.repeatIn,
            'setLang': self.setLang,
            'setTag': self.setTag,
            'removeParentNode': self.removeParentNode,
            'format': self.format,
            'formatLang': self.formatLang,
            'lang' : user.company_id.partner_id.lang,
            'translate' : self._translate,
            'setHtmlImage' : self.set_html_image,
            'strip_name' : self._strip_name,
            'time' : time,
            # more context members are setup in setCompany() below:
            #  - company_id
            #  - logo
        }
        self.setCompany(user.company_id)
        self.localcontext.update(context)
        self.name = name
        self._node = None
        self.parents = parents
        self.tag = tag
        self._lang_cache = {}
        self.lang_dict = {}
        self.default_lang = {}
        self.lang_dict_called = False
        self._transl_regex = re.compile('(\[\[.+?\]\])')

    def setTag(self, oldtag, newtag, attrs=None):
        return newtag, attrs

    def _ellipsis(self, char, size=100, truncation_str='...'):
        if len(char) <= size:
            return char
        return char[:size-len(truncation_str)] + truncation_str

    def setCompany(self, company_id):
        if company_id:
            self.localcontext['company'] = company_id
            self.localcontext['logo'] = company_id.logo
            self.rml_header = company_id.rml_header
            self.rml_header2 = company_id.rml_header2
            self.rml_header3 = company_id.rml_header3
            self.logo = company_id.logo

    def _strip_name(self, name, maxlen=50):
        return self._ellipsis(name, maxlen)

    def format(self, text, oldtag=None):
        return text.strip()

    def removeParentNode(self, tag=None):
        raise GeneratorExit('Skip')

    def set_html_image(self,id,model=None,field=None,context=None):
        if not id :
            return ''
        if not model:
            model = 'ir.attachment'
        try :
            id = int(id)
            res = self.pool.get(model).read(self.cr,self.uid,id)
            if field :
                return res[field]
            elif model =='ir.attachment' :
                return res['datas']
            else :
                return ''
        except Exception:
            return ''

    def setLang(self, lang):
        self.localcontext['lang'] = lang
        self.lang_dict_called = False
        for obj in self.objects:
            obj._context['lang'] = lang

    def _get_lang_dict(self):
        pool_lang = self.pool.get('res.lang')
        lang = self.localcontext.get('lang', 'en_US') or 'en_US'
        lang_ids = pool_lang.search(self.cr,self.uid,[('code','=',lang)])[0]
        lang_obj = pool_lang.browse(self.cr,self.uid,lang_ids)
        self.lang_dict.update({'lang_obj':lang_obj,'date_format':lang_obj.date_format,'time_format':lang_obj.time_format})
        self.default_lang[lang] = self.lang_dict.copy()
        return True

    def digits_fmt(self, obj=None, f=None, dp=None):
        digits = self.get_digits(obj, f, dp)
        return "%%.%df" % (digits, )

    def get_digits(self, obj=None, f=None, dp=None):
        d = DEFAULT_DIGITS = 2
        if dp:
            decimal_precision_obj = self.pool.get('decimal.precision')
            ids = decimal_precision_obj.search(self.cr, self.uid, [('name', '=', dp)])
            if ids:
                d = decimal_precision_obj.browse(self.cr, self.uid, ids)[0].digits
        elif obj and f:
            res_digits = getattr(obj._columns[f], 'digits', lambda x: ((16, DEFAULT_DIGITS)))
            if isinstance(res_digits, tuple):
                d = res_digits[1]
            else:
                d = res_digits(self.cr)[1]
        elif (hasattr(obj, '_field') and\
                isinstance(obj._field, (float_class, function_class)) and\
                obj._field.digits):
                d = obj._field.digits[1] or DEFAULT_DIGITS
        return d

    def formatLang(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        """
            Assuming 'Account' decimal.precision=3:
                formatLang(value) -> digits=2 (default)
                formatLang(value, digits=4) -> digits=4
                formatLang(value, dp='Account') -> digits=3
                formatLang(value, digits=5, dp='Account') -> digits=5
        """
        if digits is None:
            if dp:
                digits = self.get_digits(dp=dp)
            else:
                digits = self.get_digits(value)

        if isinstance(value, (str, unicode)) and not value:
            return ''

        if not self.lang_dict_called:
            self._get_lang_dict()
            self.lang_dict_called = True

        if date or date_time:
            if not str(value):
                return ''

            date_format = self.lang_dict['date_format']
            parse_format = DT_FORMAT
            if date_time:
                value=value.split('.')[0]
                date_format = date_format + " " + self.lang_dict['time_format']
                parse_format = DHM_FORMAT
            if not isinstance(value, time.struct_time):
                return time.strftime(date_format, time.strptime(value, parse_format))

            else:
                date = datetime(*value.timetuple()[:6])
            return date.strftime(date_format)

        res = self.lang_dict['lang_obj'].format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)
        res = currency_obj and currency_obj.position_on_report and (currency_obj.position_on_report == 'after' and '%s %s'%(res,currency_obj.symbol) or '%s %s'%(currency_obj.symbol, res) ) or res
        return res

    def repeatIn(self, lst, name,nodes_parent=False):
        ret_lst = []
        for id in lst:
            ret_lst.append({name:id})
        return ret_lst

    def _translate(self,text):
        lang = self.localcontext['lang']
        if lang and text and not text.isspace():
            transl_obj = self.pool.get('ir.translation')
            piece_list = self._transl_regex.split(text)
            for pn in range(len(piece_list)):
                if not self._transl_regex.match(piece_list[pn]):
                    source_string = piece_list[pn].replace('\n', ' ').strip()
                    if len(source_string):
                        translated_string = transl_obj._get_source(self.cr, self.uid, self.name, ('report', 'rml'), lang, source_string)
                        if translated_string:
                            piece_list[pn] = piece_list[pn].replace(source_string, translated_string)
            text = ''.join(piece_list)
        return text

    def _add_header(self, rml_dom, header='external'):
        if header=='internal':
            rml_head =  self.rml_header2
        elif header=='internal landscape':
            rml_head =  self.rml_header3
        else:
            rml_head =  self.rml_header

        head_dom = etree.XML(rml_head)
        for tag in head_dom:
            found = rml_dom.find('.//'+tag.tag)
            if found is not None and len(found):
                if tag.get('position'):
                    found.append(tag)
                else :
                    found.getparent().replace(found,tag)
        return True

    def set_context(self, objects, data, ids, report_type = None):
        self.localcontext['data'] = data
        self.localcontext['objects'] = objects
        self.localcontext['digits_fmt'] = self.digits_fmt
        self.localcontext['get_digits'] = self.get_digits
        self.datas = data
        self.ids = ids
        self.objects = objects
        if report_type:
            if report_type=='odt' :
                self.localcontext.update({'name_space' :common.odt_namespace})
            else:
                self.localcontext.update({'name_space' :common.sxw_namespace})

        # WARNING: the object[0].exists() call below is slow but necessary because
        # some broken reporting wizards pass incorrect IDs (e.g. ir.ui.menu ids)
        if objects and len(objects) == 1 and \
            objects[0].exists() and 'company_id' in objects[0] and objects[0].company_id:
            # When we print only one record, we can auto-set the correct
            # company in the localcontext. For other cases the report
            # will have to call setCompany() inside the main repeatIn loop.
            self.setCompany(objects[0].company_id)

class report_sxw(report_rml, preprocess.report):
    def __init__(self, name, table, rml=False, parser=rml_parse, header='external', store=False):
        report_rml.__init__(self, name, table, rml, '')
        self.name = name
        self.parser = parser
        self.header = header
        self.store = store
        self.internal_header=False
        if header=='internal' or header=='internal landscape':
            self.internal_header=True

    def getObjects(self, cr, uid, ids, context):
        table_obj = pooler.get_pool(cr.dbname).get(self.table)
        return table_obj.browse(cr, uid, ids, list_class=browse_record_list, context=context, fields_process=_fields_process)

    def create(self, cr, uid, ids, data, context=None):
        if self.internal_header:
            context.update({'internal_header':self.internal_header})
        pool = pooler.get_pool(cr.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cr, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:
            report_xml = ir_obj.browse(cr, uid, report_xml_ids[0], context=context)
        else:
            title = ''
            report_file = tools.file_open(self.tmpl, subdir=None)
            try:
                rml = report_file.read()
                report_type= data.get('report_type', 'pdf')
                class a(object):
                    def __init__(self, *args, **argv):
                        for key,arg in argv.items():
                            setattr(self, key, arg)
                report_xml = a(title=title, report_type=report_type, report_rml_content=rml, name=title, attachment=False, header=self.header)
            finally:
                report_file.close()
        if report_xml.header:
            report_xml.header = self.header
        report_type = report_xml.report_type
        if report_type in ['sxw','odt']:
            fnct = self.create_source_odt
        elif report_type in ['pdf','raw','txt','html']:
            fnct = self.create_source_pdf
        elif report_type=='html2html':
            fnct = self.create_source_html2html
        elif report_type=='mako2html':
            fnct = self.create_source_mako2html
        else:
            raise NotImplementedError(_('Unknown report type: %s') % report_type)
        fnct_ret = fnct(cr, uid, ids, data, report_xml, context)
        if not fnct_ret:
            return (False,False)
        return fnct_ret

    def create_source_odt(self, cr, uid, ids, data, report_xml, context=None):
        return self.create_single_odt(cr, uid, ids, data, report_xml, context or {})

    def create_source_html2html(self, cr, uid, ids, data, report_xml, context=None):
        return self.create_single_html2html(cr, uid, ids, data, report_xml, context or {})

    def create_source_mako2html(self, cr, uid, ids, data, report_xml, context=None):
        return self.create_single_mako2html(cr, uid, ids, data, report_xml, context or {})

    def create_source_pdf(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context={}
        pool = pooler.get_pool(cr.dbname)
        attach = report_xml.attachment
        if attach:
            objs = self.getObjects(cr, uid, ids, context)
            results = []
            for obj in objs:
                aname = eval(attach, {'object':obj, 'time':time})
                result = False
                if report_xml.attachment_use and aname and context.get('attachment_use', True):
                    aids = pool.get('ir.attachment').search(cr, uid, [('datas_fname','=',aname+'.pdf'),('res_model','=',self.table),('res_id','=',obj.id)])
                    if aids:
                        brow_rec = pool.get('ir.attachment').browse(cr, uid, aids[0])
                        if not brow_rec.datas:
                            continue
                        d = base64.decodestring(brow_rec.datas)
                        results.append((d,'pdf'))
                        continue
                result = self.create_single_pdf(cr, uid, [obj.id], data, report_xml, context)
                if not result:
                    return False
                if aname:
                    try:
                        name = aname+'.'+result[1]
                        pool.get('ir.attachment').create(cr, uid, {
                            'name': aname,
                            'datas': base64.encodestring(result[0]),
                            'datas_fname': name,
                            'res_model': self.table,
                            'res_id': obj.id,
                            }, context=context
                        )
                    except Exception:
                        #TODO: should probably raise a proper osv_except instead, shouldn't we? see LP bug #325632
                        logging.getLogger('report').error('Could not create saved report attachment', exc_info=True)
                results.append(result)
            if results:
                if results[0][1]=='pdf':
                    from pyPdf import PdfFileWriter, PdfFileReader
                    output = PdfFileWriter()
                    for r in results:
                        reader = PdfFileReader(cStringIO.StringIO(r[0]))
                        for page in range(reader.getNumPages()):
                            output.addPage(reader.getPage(page))
                    s = cStringIO.StringIO()
                    output.write(s)
                    return s.getvalue(), results[0][1]
        return self.create_single_pdf(cr, uid, ids, data, report_xml, context)

    def create_single_pdf(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context={}
        logo = None
        context = context.copy()
        title = report_xml.name
        rml = report_xml.report_rml_content
        # if no rml file is found
        if not rml:
            return False
        rml_parser = self.parser(cr, uid, self.name2, context=context)
        objs = self.getObjects(cr, uid, ids, context)
        rml_parser.set_context(objs, data, ids, report_xml.report_type)
        processed_rml = etree.XML(rml)
        if report_xml.header:
            rml_parser._add_header(processed_rml, self.header)
        processed_rml = self.preprocess_rml(processed_rml,report_xml.report_type)
        if rml_parser.logo:
            logo = base64.decodestring(rml_parser.logo)
        create_doc = self.generators[report_xml.report_type]
        pdf = create_doc(etree.tostring(processed_rml),rml_parser.localcontext,logo,title.encode('utf8'))
        return (pdf, report_xml.report_type)

    def create_single_odt(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context={}
        context = context.copy()
        report_type = report_xml.report_type
        context['parents'] = sxw_parents

        # if binary content was passed as unicode, we must
        # re-encode it as a 8-bit string using the pass-through
        # 'latin1' encoding, to restore the original byte values.
        # See also osv.fields.sanitize_binary_value()
        binary_report_content = report_xml.report_sxw_content.encode("latin1")

        sxw_io = StringIO.StringIO(binary_report_content)
        sxw_z = zipfile.ZipFile(sxw_io, mode='r')
        rml = sxw_z.read('content.xml')
        meta = sxw_z.read('meta.xml')
        mime_type = sxw_z.read('mimetype')
        if mime_type == 'application/vnd.sun.xml.writer':
            mime_type = 'sxw'
        else :
            mime_type = 'odt'
        sxw_z.close()

        rml_parser = self.parser(cr, uid, self.name2, context=context)
        rml_parser.parents = sxw_parents
        rml_parser.tag = sxw_tag
        objs = self.getObjects(cr, uid, ids, context)
        rml_parser.set_context(objs, data, ids, mime_type)

        rml_dom_meta = node = etree.XML(meta)
        elements = node.findall(rml_parser.localcontext['name_space']["meta"]+"user-defined")
        for pe in elements:
            if pe.get(rml_parser.localcontext['name_space']["meta"]+"name"):
                if pe.get(rml_parser.localcontext['name_space']["meta"]+"name") == "Info 3":
                    pe[0].text=data['id']
                if pe.get(rml_parser.localcontext['name_space']["meta"]+"name") == "Info 4":
                    pe[0].text=data['model']
        meta = etree.tostring(rml_dom_meta, encoding='utf-8',
                              xml_declaration=True)

        rml_dom =  etree.XML(rml)
        elements = []
        key1 = rml_parser.localcontext['name_space']["text"]+"p"
        key2 = rml_parser.localcontext['name_space']["text"]+"drop-down"
        for n in rml_dom.iterdescendants():
            if n.tag == key1:
                elements.append(n)
        if mime_type == 'odt':
            for pe in elements:
                e = pe.findall(key2)
                for de in e:
                    pp=de.getparent()
                    if de.text or de.tail:
                        pe.text = de.text or de.tail
                    for cnd in de:
                        if cnd.text or cnd.tail:
                            if pe.text:
                                pe.text +=  cnd.text or cnd.tail
                            else:
                                pe.text =  cnd.text or cnd.tail
                            pp.remove(de)
        else:
            for pe in elements:
                e = pe.findall(key2)
                for de in e:
                    pp = de.getparent()
                    if de.text or de.tail:
                        pe.text = de.text or de.tail
                    for cnd in de:
                        text = cnd.get("{http://openoffice.org/2000/text}value",False)
                        if text:
                            if pe.text and text.startswith('[['):
                                pe.text +=  text
                            elif text.startswith('[['):
                                pe.text =  text
                            if de.getparent():
                                pp.remove(de)

        rml_dom = self.preprocess_rml(rml_dom, mime_type)
        create_doc = self.generators[mime_type]
        odt = etree.tostring(create_doc(rml_dom, rml_parser.localcontext),
                             encoding='utf-8', xml_declaration=True)
        sxw_z = zipfile.ZipFile(sxw_io, mode='a')
        sxw_z.writestr('content.xml', odt)
        sxw_z.writestr('meta.xml', meta)

        if report_xml.header:
            #Add corporate header/footer
            rml_file = tools.file_open(os.path.join('base', 'report', 'corporate_%s_header.xml' % report_type))
            try:
                rml = rml_file.read()
                rml_parser = self.parser(cr, uid, self.name2, context=context)
                rml_parser.parents = sxw_parents
                rml_parser.tag = sxw_tag
                objs = self.getObjects(cr, uid, ids, context)
                rml_parser.set_context(objs, data, ids, report_xml.report_type)
                rml_dom = self.preprocess_rml(etree.XML(rml),report_type)
                create_doc = self.generators[report_type]
                odt = create_doc(rml_dom,rml_parser.localcontext)
                if report_xml.header:
                    rml_parser._add_header(odt)
                odt = etree.tostring(odt, encoding='utf-8',
                                     xml_declaration=True)
                sxw_z.writestr('styles.xml', odt)
            finally:
                rml_file.close()
        sxw_z.close()
        final_op = sxw_io.getvalue()
        sxw_io.close()
        return (final_op, mime_type)

    def create_single_html2html(self, cr, uid, ids, data, report_xml, context=None):
        if not context:
            context = {}
        context = context.copy()
        report_type = 'html'
        context['parents'] = html_parents

        html = report_xml.report_rml_content
        html_parser = self.parser(cr, uid, self.name2, context=context)
        html_parser.parents = html_parents
        html_parser.tag = sxw_tag
        objs = self.getObjects(cr, uid, ids, context)
        html_parser.set_context(objs, data, ids, report_type)

        html_dom =  etree.HTML(html)
        html_dom = self.preprocess_rml(html_dom,'html2html')

        create_doc = self.generators['html2html']
        html = etree.tostring(create_doc(html_dom, html_parser.localcontext))

        return (html.replace('&amp;','&').replace('&lt;', '<').replace('&gt;', '>').replace('</br>',''), report_type)

    def create_single_mako2html(self, cr, uid, ids, data, report_xml, context=None):
        mako_html = report_xml.report_rml_content
        html_parser = self.parser(cr, uid, self.name2, context)
        objs = self.getObjects(cr, uid, ids, context)
        html_parser.set_context(objs, data, ids, 'html')
        create_doc = self.generators['makohtml2html']
        html = create_doc(mako_html,html_parser.localcontext)
        return (html,'html')

