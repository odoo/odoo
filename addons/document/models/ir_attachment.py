# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import zipfile
import xml.dom.minidom
from StringIO import StringIO

import pyPdf

import openerp
from openerp.osv import fields, osv

_logger = logging.getLogger(__name__)

class IrAttachment(osv.osv):
    _inherit = 'ir.attachment'

    def _index_odt(self, bin_data):
        buf = u""
        f = StringIO(bin_data)
        if zipfile.is_zipfile(f):
            try:
                zf = zipfile.ZipFile(f)
                self.content = xml.dom.minidom.parseString(zf.read("content.xml"))
                for val in ["text:p", "text:h", "text:list"]:
                    for element in self.content.getElementsByTagName(val) :
                        for node in element.childNodes :
                            if node.nodeType == xml.dom.Node.TEXT_NODE :
                                buf += node.nodeValue
                            elif node.nodeType == xml.dom.Node.ELEMENT_NODE :
                                buf += self.textToString(node)
                        buf += "\n"
            except Exception:
                pass
        return buf

    def _index_pdf(self, bin_data):
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
        # try to index odt content
        buf = self._index_odt(bin_data)
        if buf:
            return buf
        # try to index pdf content
        buf = self._index_pdf(bin_data)
        if buf:
            return buf

        return super(IrAttachment, self)._index(cr, uid, bin_data, datas_fname, mimetype)

