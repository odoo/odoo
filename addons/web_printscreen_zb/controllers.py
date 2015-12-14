# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2013 ZestyBeanz Technologies Pvt. Ltd.
#    (http://wwww.zbeanztech.com)
#    contact@zbeanztech.com
#    prajul@zbeanztech.com
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

try:
    import json
except ImportError:
    import simplejson as json
import openerp.addons.web.http as openerpweb
from openerp.addons.web.controllers.main import ExcelExport
from openerp.addons.web.controllers.main import Export
import re
from cStringIO import StringIO
from lxml  import etree
import trml2pdf
import time, os
import locale
import openerp.tools as tools
try:
    import xlwt
except ImportError:
    xlwt = None
import logging
_logger = logging.getLogger(__name__)

class ZbExcelExport(ExcelExport):
    _cp_path = '/web/export/zb_excel_export'

    def from_data(self, fields, rows):
	#_logger.info('FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFf fields: %s', fields)
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        style = xlwt.easyxf('align: wrap yes')
        font = xlwt.Font()
        font.bold = True
        style.font = font
        ignore_index = []
        count = 0
        for i, fieldname in enumerate(fields):
            if fieldname.get('header_data_id', False):
                field_name = fieldname.get('header_name', '')
                worksheet.write(0, i-count, field_name, style)
                worksheet.col(i).width = 8000
            else:
                count += 1
                ignore_index.append(i)
        style = xlwt.easyxf('align: wrap yes')
        bold_style = xlwt.easyxf('align: wrap yes')
        font = xlwt.Font()
        font.bold = True
        bold_style.font = font
        for row_index, row in enumerate(rows):
            count = 0
            for cell_index, cell_value in enumerate(row):
                if cell_index not in ignore_index:
                    cell_style = style
                    if cell_value.get('bold', False):
                        cell_style = bold_style
                    cellvalue = cell_value.get('data', '')
                    if isinstance(cellvalue, basestring):
                        cellvalue = re.sub("\r", " ", cellvalue)
                    if cell_value.get('number', False) and cellvalue:
                        cellvalue = float(cellvalue)
                    if cellvalue is False: cellvalue = None
                    worksheet.write(row_index + 1, cell_index - count, cellvalue, cell_style)
                else:
                    count += 1
        fp = StringIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        return data
    
    @openerpweb.httprequest
    def index(self, req, data, token):
        data = json.loads(data)
	#_logger.info('GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG data: %s', data)
        return req.make_response(
            self.from_data(data.get('headers', []), data.get('rows', [])),
                           headers=[
                                    ('Content-Disposition', 'attachment; filename="%s"'
                                        % data.get('model', 'Export.xls')),
                                    ('Content-Type', self.content_type)
                                    ],
                                 cookies={'fileToken': token}
                                 )

class ExportPdf(Export):
    _cp_path = '/web/export/zb_pdf'
    fmt = {
        'tag': 'pdf',
        'label': 'PDF',
        'error': None
    }
    
    @property
    def content_type(self):
        return 'application/pdf'
    
    def filename(self, base):
        return base + '.pdf'
    
    def from_data(self, uid, fields, rows, company_name):
        pageSize=[210.0,297.0]
        new_doc = etree.Element("report")
        config = etree.SubElement(new_doc, 'config')
        def _append_node(name, text):
            n = etree.SubElement(config, name)
            n.text = text
        _append_node('date', time.strftime(str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))))
        _append_node('PageSize', '%.2fmm,%.2fmm' % tuple(pageSize))
        _append_node('PageWidth', '%.2f' % (pageSize[0] * 2.8346,))
        _append_node('PageHeight', '%.2f' %(pageSize[1] * 2.8346,))
        _append_node('PageFormat', 'a4')
        _append_node('header-date', time.strftime(str(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'))))
        _append_node('company', company_name)
        l = []
        t = 0
        temp = []
        tsum = []
        skip_index = []
        header = etree.SubElement(new_doc, 'header')
        i = 0
        for f in fields:
            if f.get('header_data_id', False):
                value = f.get('header_name', "")
                field = etree.SubElement(header, 'field')
                field.text = tools.ustr(value)
            else:
                skip_index.append(i)
            i += 1
        lines = etree.SubElement(new_doc, 'lines')
        for row_lines in rows:
            node_line = etree.SubElement(lines, 'row')
            j = 0
            for row in row_lines:
                if not j in skip_index:
                    para = "yes"
                    tree = "no"
                    value = row.get('data', '')
                    if row.get('bold', False):
                        para = "group"
                    if row.get('number', False):
                        tree = "float"
                    col = etree.SubElement(node_line, 'col', para=para, tree=tree)
                    col.text = tools.ustr(value)
                j += 1
        transform = etree.XSLT(
            etree.parse(os.path.join(tools.config['root_path'],
                                     'addons/base/report/custom_new.xsl')))
        rml = etree.tostring(transform(new_doc))
        self.obj = trml2pdf.parseNode(rml, title='Printscreen')
        return self.obj

class ZbPdfExport(ExportPdf):
    _cp_path = '/web/export/zb_pdf_export'
    
    @openerpweb.httprequest
    def index(self, req, data, token):
        data = json.loads(data)
        uid = data.get('uid', False)
        return req.make_response(self.from_data(uid, data.get('headers', []), data.get('rows', []),
                                                data.get('company_name','')),
                                 headers=[('Content-Disposition',
                                           'attachment; filename=PDF Export'),
                                          ('Content-Type', self.content_type)],
                                 cookies={'fileToken': bytes(token)})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
