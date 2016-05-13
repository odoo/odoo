# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import zipfile
import xml.dom.minidom
from StringIO import StringIO

import pyPdf

from openerp.osv import osv

_logger = logging.getLogger(__name__)
FTYPES = ['docx', 'pptx', 'xlsx', 'opendoc', 'pdf']

# Keep function in case it is necessary to do toUnicode(buf.encode('ascii', 'replace'))
def toUnicode(s):
    try:
        return s.decode('utf-8')
    except UnicodeError:
        try:
            return s.decode('latin')
        except UnicodeError:
            try:
                return s.encode('ascii')
            except UnicodeError:
                return s

def textToString(element):
    buff = u""
    for node in element.childNodes:
        if node.nodeType == xml.dom.Node.TEXT_NODE:
            buff += node.nodeValue
        elif node.nodeType == xml.dom.Node.ELEMENT_NODE:
            buff += textToString(node)
    return buff


class IrAttachment(osv.osv):
    _inherit = 'ir.attachment'

    def _index_docx(self, bin_data):
        '''Index Microsoft .docx documents'''
        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("word/document.xml"))
                for val in ["w:p", "w:h", "text:list"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_pptx(self, bin_data):
        '''Index Microsoft .pptx documents'''

        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                zf_filelist = [x for x in zf.namelist() if x.startswith('ppt/slides/slide')]
                for i in range(1, len(zf_filelist) + 1):
                    content = xml.dom.minidom.parseString(zf.read('ppt/slides/slide%s.xml' % i))
                    for val in ["a:t"]:
                        for element in content.getElementsByTagName(val):
                            buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_xlsx(self, bin_data):
        '''Index Microsoft .xlsx documents'''

        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("xl/sharedStrings.xml"))
                for val in ["t"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_opendoc(self, bin_data):
        '''Index OpenDocument documents (.odt, .ods...)'''

        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                content = xml.dom.minidom.parseString(zf.read("content.xml"))
                for val in ["text:p", "text:h", "text:list"]:
                    for element in content.getElementsByTagName(val):
                        buf += textToString(element) + "\n"
            except Exception:
                pass
        return buf

    def _index_pdf(self, bin_data):
        '''Index PDF documents'''

        buf = u""
        if bin_data.startswith('%PDF-'):
            f = StringIO(bin_data)
            try:
                pdf = pyPdf.PdfFileReader(f)
                for page in pdf.pages:
                    buf += page.extractText()
            except Exception:
                pass
        return buf

    def _index(self, cr, uid, bin_data, datas_fname, mimetype):
        for ftype in FTYPES:
            buf = getattr(self, '_index_%s' % ftype)(bin_data)
            if buf:
                return buf

        return super(IrAttachment, self)._index(cr, uid, bin_data, datas_fname, mimetype)
