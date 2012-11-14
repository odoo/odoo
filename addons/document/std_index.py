# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from content_index import indexer, cntIndex
from subprocess import Popen, PIPE
import StringIO
import odt2txt
import sys, zipfile, xml.dom.minidom
import logging
_logger = logging.getLogger(__name__)

def _to_unicode(s):
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
    buffer = u""
    for node in element.childNodes :
        if node.nodeType == xml.dom.Node.TEXT_NODE :
            buffer += node.nodeValue
        elif node.nodeType == xml.dom.Node.ELEMENT_NODE :
            buffer += textToString(node)
    return buffer
        
class TxtIndex(indexer):
    def _getMimeTypes(self):
        return ['text/plain','text/html','text/diff','text/xml', 'text/*', 
            'application/xml']
    
    def _getExtensions(self):
        return ['.txt', '.py']

    def _doIndexContent(self, content):
        return content

cntIndex.register(TxtIndex())

class PptxIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/vnd.openxmlformats-officedocument.presentationml.presentation']
    
    def _getExtensions(self):
        return ['.pptx']

    def _doIndexFile(self, fname):
        def toString () :
            """ Converts the document to a string. """
            buffer = u""
            for val in ["a:t"]:
                for paragraph in content.getElementsByTagName(val) :
                    buffer += textToString(paragraph) + "\n"
            return buffer

        data = []
        zip = zipfile.ZipFile(fname)
        files = filter(lambda x: x.startswith('ppt/slides/slide'), zip.namelist())
        for i in range(1, len(files) + 1):
            content = xml.dom.minidom.parseString(zip.read('ppt/slides/slide%s.xml' % str(i)))
            res = toString().encode('ascii','replace')
            data.append(res)

        return _to_unicode('\n'.join(data))

cntIndex.register(PptxIndex())

class DocIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/ms-word']
    
    def _getExtensions(self):
        return ['.doc']

    def _doIndexFile(self, fname):
        try:
            pop = Popen(['antiword', fname], shell=False, stdout=PIPE)
            (data, _) = pop.communicate()
            return _to_unicode(data)
        except OSError:
            
            _logger.warning("Failed attempt to execute antiword (MS Word reader). Antiword is necessary to index the file %s of MIME type %s. Detailed error available at DEBUG level.", fname, self._getMimeTypes()[0])
            _logger.debug("Trace of the failed file indexing attempt.", exc_info=True)
            return False
    
cntIndex.register(DocIndex())

class DocxIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']

    def _getExtensions(self):
        return ['.docx']

    def _doIndexFile(self, fname):
        zip = zipfile.ZipFile(fname)
        content = xml.dom.minidom.parseString(zip.read("word/document.xml"))
        def toString () :
            """ Converts the document to a string. """
            buffer = u""
            for val in ["w:p", "w:h", "text:list"]:
                for paragraph in content.getElementsByTagName(val) :
                    buffer += textToString(paragraph) + "\n"
            return buffer

        res = toString().encode('ascii','replace')

        return _to_unicode(res)

cntIndex.register(DocxIndex())


class XlsxIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']

    def _getExtensions(self):
        return ['.xlsx']

    def _doIndexFile(self, fname):
        zip = zipfile.ZipFile(fname)
        content = xml.dom.minidom.parseString(zip.read("xl/sharedStrings.xml"))
        def toString () :
            """ Converts the document to a string. """
            buffer = u""
            for val in ["t"]:
                for paragraph in content.getElementsByTagName(val) :
                    buffer += textToString(paragraph) + "\n"
            return buffer

        res = toString().encode('ascii','replace')

        return _to_unicode(res)

cntIndex.register(XlsxIndex())

class PdfIndex(indexer):
    def _getMimeTypes(self):
        return [ 'application/pdf']
    
    def _getExtensions(self):
        return ['.pdf']

    def _doIndexFile(self, fname):
        pop = Popen(['pdftotext', '-enc', 'UTF-8', '-nopgbrk', fname, '-'], shell=False, stdout=PIPE)
        (data, _) = pop.communicate()
        return _to_unicode(data)

cntIndex.register(PdfIndex())

class ImageNoIndex(indexer):
    def _getMimeTypes(self):
        return [ 'image/*']
    
    def _getExtensions(self):
        #better return no extension, and let 'file' do its magic
        return []
        #return ['.png','.jpg','.gif','.jpeg','.bmp','.tiff']

    def _doIndexContent(self, content):
        return 'image'


cntIndex.register(ImageNoIndex())

# other opendocument formats:
# chart-template chart database
# formula-template formula graphics-template graphics
# image
# presentation-template presentation spreadsheet-template spreadsheet

class OpenDoc(indexer):
    """ Index OpenDocument files.
    
        Q: is it really worth it to index spreadsheets, or do we only get a
        meaningless list of numbers (cell contents) ?
        """
    def _getMimeTypes(self):
        otypes = [ 'text', 'text-web', 'text-template', 'text-master' ]
        return map(lambda a: 'application/vnd.oasis.opendocument.'+a, otypes)
    
    def _getExtensions(self):
        return ['.odt', '.ott', ] # '.ods'

    def _doIndexContent(self, content):
        s = StringIO.StringIO(content)
        o = odt2txt.OpenDocumentTextFile(s)
        result = _to_unicode(o.toString())
        s.close()
        return result

cntIndex.register(OpenDoc())


#eof

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
