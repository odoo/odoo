# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
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
import openerp.tools as tools
import zipfile
import common
from openerp.exceptions import AccessError

import openerp
from openerp import SUPERUSER_ID
from openerp.osv.fields import float as float_field, function as function_field, datetime as datetime_field
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval as eval

_logger = logging.getLogger(__name__)

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

def get_date_length(date_format=DEFAULT_SERVER_DATE_FORMAT):
    return len((datetime.now()).strftime(date_format))


class rml_parse(object):
    def __init__(self, cr, uid, name, parents=rml_parents, tag=rml_tag, context=None):
        if not context:
            context={}
        self.cr = cr
        self.uid = uid
        self.pool = openerp.registry(cr.dbname)
        user = self.pool['res.users'].browse(cr, uid, uid, context=context)
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
            'display_address': self.display_address,
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
        if not char:
            return ''
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
            res = self.pool[model].read(self.cr,self.uid,id)
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
        # re-evaluate self.objects in a different environment
        env = self.objects.env(self.cr, self.uid, self.localcontext)
        self.objects = self.objects.with_env(env)

    def _get_lang_dict(self):
        pool_lang = self.pool['res.lang']
        lang = self.localcontext.get('lang', 'en_US') or 'en_US'
        lang_ids = pool_lang.search(self.cr,self.uid,[('code','=',lang)])
        if not lang_ids:
            lang_ids = pool_lang.search(self.cr,self.uid,[('code','=','en_US')])
        lang_obj = pool_lang.browse(self.cr,self.uid,lang_ids[0])
        self.lang_dict.update({'lang_obj':lang_obj,'date_format':lang_obj.date_format,'time_format':lang_obj.time_format})
        self.default_lang[lang] = self.lang_dict.copy()
        return True

    def digits_fmt(self, obj=None, f=None, dp=None):
        digits = self.get_digits(obj, f, dp)
        return "%%.%df" % (digits, )

    def get_digits(self, obj=None, f=None, dp=None):
        d = DEFAULT_DIGITS = 2
        if dp:
            decimal_precision_obj = self.pool['decimal.precision']
            d = decimal_precision_obj.precision_get(self.cr, self.uid, dp)
        elif obj and f:
            res_digits = getattr(obj._columns[f], 'digits', lambda x: ((16, DEFAULT_DIGITS)))
            if isinstance(res_digits, tuple):
                d = res_digits[1]
            else:
                d = res_digits(self.cr)[1]
        elif (hasattr(obj, '_field') and\
                isinstance(obj._field, (float_field, function_field)) and\
                obj._field.digits):
                d = obj._field.digits[1]
                if not d and d is not 0:
                    d = DEFAULT_DIGITS
        return d

    def formatLang(self, value, digits=None, date=False, date_time=False, grouping=True, monetary=False, dp=False, currency_obj=False):
        if digits is None:
            if dp:
                digits = self.get_digits(dp=dp)
            elif currency_obj:
                digits = currency_obj.decimal_places
            else:
                digits = self.get_digits(value)

        if isinstance(value, (str, unicode)) and not value:
            return ''

        if not self.lang_dict_called:
            self._get_lang_dict()
            self.lang_dict_called = True

        if date or date_time:
            if not value:
                return ''

            date_format = self.lang_dict['date_format']
            parse_format = DEFAULT_SERVER_DATE_FORMAT
            if date_time:
                value = value.split('.')[0]
                date_format = date_format + " " + self.lang_dict['time_format']
                parse_format = DEFAULT_SERVER_DATETIME_FORMAT
            if isinstance(value, basestring):
                # FIXME: the trimming is probably unreliable if format includes day/month names
                #        and those would need to be translated anyway.
                date = datetime.strptime(value[:get_date_length(parse_format)], parse_format)
            elif isinstance(value, time.struct_time):
                date = datetime(*value[:6])
            else:
                date = datetime(*value.timetuple()[:6])
            if date_time:
                # Convert datetime values to the expected client/context timezone
                date = datetime_field.context_timestamp(self.cr, self.uid,
                                                        timestamp=date,
                                                        context=self.localcontext)
            return date.strftime(date_format.encode('utf-8'))

        res = self.lang_dict['lang_obj'].format('%.' + str(digits) + 'f', value, grouping=grouping, monetary=monetary)
        if currency_obj:
            if currency_obj.position == 'after':
                res = u'%s\N{NO-BREAK SPACE}%s' % (res, currency_obj.symbol)
            elif currency_obj and currency_obj.position == 'before':
                res = u'%s\N{NO-BREAK SPACE}%s' % (currency_obj.symbol, res)
        return res

    def display_address(self, address_record, without_company=False):
        # FIXME handle `without_company`
        return address_record.contact_address

    def repeatIn(self, lst, name,nodes_parent=False):
        ret_lst = []
        for id in lst:
            ret_lst.append({name:id})
        return ret_lst

    def _translate(self,text):
        lang = self.localcontext['lang']
        if lang and text and not text.isspace():
            transl_obj = self.pool['ir.translation']
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
    """
    The register=True kwarg has been added to help remove the
    openerp.netsvc.LocalService() indirection and the related
    openerp.report.interface.report_int._reports dictionary:
    report_sxw registered in XML with auto=False are also registered in Python.
    In that case, they are registered in the above dictionary. Since
    registration is automatically done upon instanciation, and that
    instanciation is needed before rendering, a way was needed to
    instanciate-without-register a report. In the future, no report
    should be registered in the above dictionary and it will be dropped.
    """
    def __init__(self, name, table, rml=False, parser=rml_parse, header='external', store=False, register=True):
        report_rml.__init__(self, name, table, rml, '', register=register)
        self.name = name
        self.parser = parser
        self.header = header
        self.store = store
        self.internal_header=False
        if header=='internal' or header=='internal landscape':
            self.internal_header=True

    def getObjects(self, cr, uid, ids, context):
        table_obj = openerp.registry(cr.dbname)[self.table]
        return table_obj.browse(cr, uid, ids, context=context)

    def create(self, cr, uid, ids, data, context=None):
        context = dict(context or {})
        if self.internal_header:
            context.update(internal_header=self.internal_header)

        # skip osv.fields.sanitize_binary_value() because we want the raw bytes in all cases
        context.update(bin_raw=True)
        registry = openerp.registry(cr.dbname)
        ir_obj = registry['ir.actions.report.xml']
        registry['res.font'].font_scan(cr, SUPERUSER_ID, lazy=True, context=context)

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

        # We add an attribute on the ir.actions.report.xml instance.
        # This attribute 'use_global_header' will be used by
        # the create_single_XXX function of the report engine.
        # This change has been done to avoid a big change of the API.
        setattr(report_xml, 'use_global_header', self.header if report_xml.header else False)

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
            return False, False
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
        registry = openerp.registry(cr.dbname)
        attach = report_xml.attachment
        if attach:
            objs = self.getObjects(cr, uid, ids, context)
            results = []
            for obj in objs:
                aname = eval(attach, {'object':obj, 'time':time})
                result = False
                if report_xml.attachment_use and aname and context.get('attachment_use', True):
                    aids = registry['ir.attachment'].search(cr, uid, [('datas_fname','=',aname+'.pdf'),('res_model','=',self.table),('res_id','=',obj.id)])
                    if aids:
                        brow_rec = registry['ir.attachment'].browse(cr, uid, aids[0])
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
                        # Remove the default_type entry from the context: this
                        # is for instance used on the account.account_invoices
                        # and is thus not intended for the ir.attachment type
                        # field.
                        ctx = dict(context)
                        ctx.pop('default_type', None)
                        registry['ir.attachment'].create(cr, uid, {
                            'name': aname,
                            'datas': base64.encodestring(result[0]),
                            'datas_fname': name,
                            'res_model': self.table,
                            'res_id': obj.id,
                            }, context=ctx
                        )
                    except AccessError:
                        #TODO: should probably raise a proper osv_except instead, shouldn't we? see LP bug #325632
                        _logger.info('Could not create saved report attachment', exc_info=True)
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
        if report_xml.use_global_header:
            rml_parser._add_header(processed_rml, self.header)
        processed_rml = self.preprocess_rml(processed_rml,report_xml.report_type)
        if rml_parser.logo:
            logo = base64.decodestring(rml_parser.logo)
        create_doc = self.generators[report_xml.report_type]
        pdf = create_doc(etree.tostring(processed_rml),rml_parser.localcontext,logo,title.encode('utf8'))
        return pdf, report_xml.report_type

    def create_single_odt(self, cr, uid, ids, data, report_xml, context=None):
        context = dict(context or {})
        context['parents'] = sxw_parents
        report_type = report_xml.report_type
        binary_report_content = report_xml.report_sxw_content
        if isinstance(report_xml.report_sxw_content, unicode):
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
        sxw_contents = {'content.xml':odt, 'meta.xml':meta}

        if report_xml.use_global_header:
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
                if report_xml.use_global_header:
                    rml_parser._add_header(odt)
                odt = etree.tostring(odt, encoding='utf-8',
                                     xml_declaration=True)
                sxw_contents['styles.xml'] = odt
            finally:
                rml_file.close()

        #created empty zip writing sxw contents to avoid duplication
        sxw_out = StringIO.StringIO()
        sxw_out_zip = zipfile.ZipFile(sxw_out, mode='w')
        sxw_template_zip = zipfile.ZipFile (sxw_io, 'r')
        for item in sxw_template_zip.infolist():
            if item.filename not in sxw_contents:
                buffer = sxw_template_zip.read(item.filename)
                sxw_out_zip.writestr(item.filename, buffer)
        for item_filename, buffer in sxw_contents.iteritems():
            sxw_out_zip.writestr(item_filename, buffer)
        sxw_template_zip.close()
        sxw_out_zip.close()
        final_op = sxw_out.getvalue()
        sxw_io.close()
        sxw_out.close()
        return final_op, mime_type

    def create_single_html2html(self, cr, uid, ids, data, report_xml, context=None):
        context = dict(context or {})
        context['parents'] = html_parents
        report_type = 'html'

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

        return html.replace('&amp;','&').replace('&lt;', '<').replace('&gt;', '>').replace('</br>',''), report_type

    def create_single_mako2html(self, cr, uid, ids, data, report_xml, context=None):
        mako_html = report_xml.report_rml_content
        html_parser = self.parser(cr, uid, self.name2, context)
        objs = self.getObjects(cr, uid, ids, context)
        html_parser.set_context(objs, data, ids, 'html')
        create_doc = self.generators['makohtml2html']
        html = create_doc(mako_html,html_parser.localcontext)
        return html,'html'
