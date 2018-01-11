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

import os
import re

from lxml import etree

import openerp
import openerp.tools as tools
import openerp.modules
import print_xml
import render
import urllib

from openerp import SUPERUSER_ID
from openerp.report.render.rml2pdf import customfonts

#
# coerce any type to a unicode string (to preserve non-ascii characters)
# and escape XML entities
#
def toxml(value):
    unicode_value = tools.ustr(value)
    return unicode_value.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;')

class report_int(object):

    _reports = {}
    
    def __init__(self, name, register=True):
        if register:
            assert openerp.conf.deprecation.allow_report_int_registration
            assert name.startswith('report.'), 'Report names should start with "report.".'
            assert name not in self._reports, 'The report "%s" already exists.' % name
            self._reports[name] = self
        else:
            # The report is instanciated at each use site, which is ok.
            pass

        self.__name = name

        self.name = name
        self.id = 0
        self.name2 = '.'.join(name.split('.')[1:])
        # TODO the reports have methods with a 'title' kwarg that is redundant with this attribute
        self.title = None

    def create(self, cr, uid, ids, datas, context=None):
        return False

class report_rml(report_int):
    """
        Automatically builds a document using the transformation process:
            XML -> DATAS -> RML -> PDF -> HTML
        using a XSL:RML transformation
    """
    def __init__(self, name, table, tmpl, xsl, register=True):
        super(report_rml, self).__init__(name, register=register)
        self.table = table
        self.internal_header=False
        self.tmpl = tmpl
        self.xsl = xsl
        self.bin_datas = {}
        self.generators = {
            'pdf': self.create_pdf,
            'html': self.create_html,
            'raw': self.create_raw,
            'sxw': self.create_sxw,
            'txt': self.create_txt,
            'odt': self.create_odt,
            'html2html' : self.create_html2html,
            'makohtml2html' :self.create_makohtml2html,
        }

    def create(self, cr, uid, ids, datas, context):
        registry = openerp.registry(cr.dbname)
        xml = self.create_xml(cr, uid, ids, datas, context)
        xml = tools.ustr(xml).encode('utf8')
        report_type = datas.get('report_type', 'pdf')
        if report_type == 'raw':
            return xml, report_type

        registry['res.font'].font_scan(cr, SUPERUSER_ID, lazy=True, context=context)

        rml = self.create_rml(cr, xml, uid, context)
        ir_actions_report_xml_obj = registry['ir.actions.report.xml']
        report_xml_ids = ir_actions_report_xml_obj.search(cr, uid, [('report_name', '=', self.name[7:])], context=context)
        self.title = report_xml_ids and ir_actions_report_xml_obj.browse(cr,uid,report_xml_ids)[0].name or 'OpenERP Report'
        create_doc = self.generators[report_type]
        pdf = create_doc(rml, title=self.title)
        return pdf, report_type

    def create_xml(self, cr, uid, ids, datas, context=None):
        if not context:
            context={}
        doc = print_xml.document(cr, uid, datas, {})
        self.bin_datas.update( doc.bin_datas  or {})
        doc.parse(self.tmpl, ids, self.table, context)
        xml = doc.xml_get()
        doc.close()
        return self.post_process_xml_data(cr, uid, xml, context)

    def post_process_xml_data(self, cr, uid, xml, context=None):

        if not context:
            context={}
        # find the position of the 3rd tag
        # (skip the <?xml ...?> and the "root" tag)
        iter = re.finditer('<[^>]*>', xml)
        i = iter.next()
        i = iter.next()
        pos_xml = i.end()

        doc = print_xml.document(cr, uid, {}, {})
        tmpl_path = openerp.modules.get_module_resource('base', 'report', 'corporate_defaults.xml')
        doc.parse(tmpl_path, [uid], 'res.users', context)
        corporate_header = doc.xml_get()
        doc.close()

        # find the position of the tag after the <?xml ...?> tag
        iter = re.finditer('<[^>]*>', corporate_header)
        i = iter.next()
        pos_header = i.end()

        return xml[:pos_xml] + corporate_header[pos_header:] + xml[pos_xml:]

    #
    # TODO: The translation doesn't work for "<tag t="1">textext<tag> tex</tag>text</tag>"
    #
    def create_rml(self, cr, xml, uid, context=None):
        if self.tmpl=='' and not self.internal_header:
            self.internal_header=True
        if not context:
            context={}
        registry = openerp.registry(cr.dbname)
        ir_translation_obj = registry['ir.translation']

        # In some case we might not use xsl ...
        if not self.xsl:
            return xml

        stylesheet_file = tools.file_open(self.xsl)
        try:
            stylesheet = etree.parse(stylesheet_file)
            xsl_path, _ = os.path.split(self.xsl)
            for import_child in stylesheet.findall('./import'):
                if 'href' in import_child.attrib:
                    imp_file = import_child.get('href')
                    _, imp_file = tools.file_open(imp_file, subdir=xsl_path, pathinfo=True)
                    import_child.set('href', urllib.quote(str(imp_file)))
                    imp_file.close()
        finally:
            stylesheet_file.close()

        #TODO: get all the translation in one query. That means we have to:
        # * build a list of items to translate,
        # * issue the query to translate them,
        # * (re)build/update the stylesheet with the translated items

        def translate(doc, lang):
            translate_aux(doc, lang, False)

        def translate_aux(doc, lang, t):
            for node in doc:
                t = t or node.get("t")
                if t:
                    text = None
                    tail = None
                    if node.text:
                        text = node.text.strip().replace('\n',' ')
                    if node.tail:
                        tail = node.tail.strip().replace('\n',' ')
                    if text:
                        translation1 = ir_translation_obj._get_source(cr, uid, self.name2, 'xsl', lang, text)
                        if translation1:
                            node.text = node.text.replace(text, translation1)
                    if tail:
                        translation2 = ir_translation_obj._get_source(cr, uid, self.name2, 'xsl', lang, tail)
                        if translation2:
                            node.tail = node.tail.replace(tail, translation2)
                translate_aux(node, lang, t)

        if context.get('lang', False):
            translate(stylesheet.iter(), context['lang'])

        transform = etree.XSLT(stylesheet)
        xml = etree.tostring(
            transform(etree.fromstring(xml)))

        return xml

    def create_pdf(self, rml, localcontext = None, logo=None, title=None):
        if not localcontext:
            localcontext = {}
        localcontext.update({'internal_header':self.internal_header})
        if logo:
            self.bin_datas['logo'] = logo
        else:
            if 'logo' in self.bin_datas:
                del self.bin_datas['logo']
        obj = render.rml(rml, localcontext, self.bin_datas, self._get_path(), title)
        obj.render()
        return obj.get()

    def create_html(self, rml, localcontext = None, logo=None, title=None):
        obj = render.rml2html(rml, localcontext, self.bin_datas)
        obj.render()
        return obj.get()

    def create_txt(self, rml,localcontext, logo=None, title=None):
        obj = render.rml2txt(rml, localcontext, self.bin_datas)
        obj.render()
        return obj.get().encode('utf-8')

    def create_html2html(self, rml, localcontext = None, logo=None, title=None):
        obj = render.html2html(rml, localcontext, self.bin_datas)
        obj.render()
        return obj.get()


    def create_raw(self,rml, localcontext = None, logo=None, title=None):
        obj = render.odt2odt(etree.XML(rml),localcontext)
        obj.render()
        return etree.tostring(obj.get())

    def create_sxw(self,rml,localcontext = None):
        obj = render.odt2odt(rml,localcontext)
        obj.render()
        return obj.get()

    def create_odt(self,rml,localcontext = None):
        obj = render.odt2odt(rml,localcontext)
        obj.render()
        return obj.get()

    def create_makohtml2html(self,html,localcontext = None):
        obj = render.makohtml2html(html,localcontext)
        obj.render()
        return obj.get()

    def _get_path(self):
        return [
            self.tmpl.replace(os.path.sep, '/').rsplit('/', 1)[0],
            'addons',
            tools.config['root_path']
        ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
