# -*- coding: utf-8 -*-
#
# vim: sw=4:expandtab:foldmethod=marker
#
# Copyright (c) 2006, Mathieu Fenniak
# Copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# * Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
# * The name of the author may not be used to endorse or promote products
# derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
A pure-Python PDF library with an increasing number of capabilities.
See README for links to FAQ, documentation, homepage, etc.
"""

__author__ = "Mathieu Fenniak"
__author_email__ = "biziqe@mathieu.fenniak.net"

__maintainer__ = "Phaseit, Inc."
__maintainer_email = "PyPDF2@phaseit.net"

import string
import math
import struct
import sys
import uuid
from sys import version_info
if version_info < ( 3, 0 ):
    from cStringIO import StringIO
else:
    from io import StringIO

if version_info < ( 3, 0 ):
    BytesIO = StringIO
else:
    from io import BytesIO

from . import filters
from . import utils
import warnings
import codecs
from .generic import *
from .utils import readNonWhitespace, readUntilWhitespace, ConvertFunctionsToVirtualList
from .utils import isString, b_, u_, ord_, chr_, str_, formatWarning

if version_info < ( 2, 4 ):
   from sets import ImmutableSet as frozenset

if version_info < ( 2, 5 ):
    from md5 import md5
else:
    from hashlib import md5
import uuid


class PdfFileWriter(object):
    """
    This class supports writing PDF files out, given pages produced by another
    class (typically :class:`PdfFileReader<PdfFileReader>`).
    """
    def __init__(self):
        self._header = b_("%PDF-1.3")
        self._objects = []  # array of indirect objects

        # The root of our page tree node.
        pages = DictionaryObject()
        pages.update({
                NameObject("/Type"): NameObject("/Pages"),
                NameObject("/Count"): NumberObject(0),
                NameObject("/Kids"): ArrayObject(),
                })
        self._pages = self._addObject(pages)

        # info object
        info = DictionaryObject()
        info.update({
                NameObject("/Producer"): createStringObject(codecs.BOM_UTF16_BE + u_("PyPDF2").encode('utf-16be'))
                })
        self._info = self._addObject(info)

        # root object
        root = DictionaryObject()
        root.update({
            NameObject("/Type"): NameObject("/Catalog"),
            NameObject("/Pages"): self._pages,
            })
        self._root = None
        self._root_object = root

    def _addObject(self, obj):
        self._objects.append(obj)
        return IndirectObject(len(self._objects), 0, self)

    def getObject(self, ido):
        if ido.pdf != self:
            raise ValueError("pdf must be self")
        return self._objects[ido.idnum - 1]

    def _addPage(self, page, action):
        assert page["/Type"] == "/Page"
        page[NameObject("/Parent")] = self._pages
        page = self._addObject(page)
        pages = self.getObject(self._pages)
        action(pages["/Kids"], page)
        pages[NameObject("/Count")] = NumberObject(pages["/Count"] + 1)

    def addPage(self, page):
        """
        Adds a page to this PDF file.  The page is usually acquired from a
        :class:`PdfFileReader<PdfFileReader>` instance.

        :param PageObject page: The page to add to the document. Should be
            an instance of :class:`PageObject<PyPDF2.pdf.PageObject>`
        """
        self._addPage(page, list.append)

    def insertPage(self, page, index=0):
        """
        Insert a page in this PDF file. The page is usually acquired from a
        :class:`PdfFileReader<PdfFileReader>` instance.

        :param PageObject page: The page to add to the document.  This
            argument should be an instance of :class:`PageObject<pdf.PageObject>`.
        :param int index: Position at which the page will be inserted.
        """
        self._addPage(page, lambda l, p: l.insert(index, p))

    def getPage(self, pageNumber):
        """
        Retrieves a page by number from this PDF file.

        :param int pageNumber: The page number to retrieve
            (pages begin at zero)
        :return: the page at the index given by *pageNumber*
        :rtype: :class:`PageObject<pdf.PageObject>`
        """
        pages = self.getObject(self._pages)
        # XXX: crude hack
        return pages["/Kids"][pageNumber].getObject()

    def getNumPages(self):
        """
        :return: the number of pages.
        :rtype: int
        """
        pages = self.getObject(self._pages)
        return int(pages[NameObject("/Count")])

    def addBlankPage(self, width=None, height=None):
        """
        Appends a blank page to this PDF file and returns it. If no page size
        is specified, use the size of the last page.

        :param float width: The width of the new page expressed in default user
            space units.
        :param float height: The height of the new page expressed in default
            user space units.
        :return: the newly appended page
        :rtype: :class:`PageObject<PyPDF2.pdf.PageObject>`
        :raises PageSizeNotDefinedError: if width and height are not defined
            and previous page does not exist.
        """
        page = PageObject.createBlankPage(self, width, height)
        self.addPage(page)
        return page

    def insertBlankPage(self, width=None, height=None, index=0):
        """
        Inserts a blank page to this PDF file and returns it. If no page size
        is specified, use the size of the last page.

        :param float width: The width of the new page expressed in default user
            space units.
        :param float height: The height of the new page expressed in default
            user space units.
        :param int index: Position to add the page.
        :return: the newly appended page
        :rtype: :class:`PageObject<PyPDF2.pdf.PageObject>`
        :raises PageSizeNotDefinedError: if width and height are not defined
            and previous page does not exist.
        """
        if width is None or height is None and \
                (self.getNumPages() - 1) >= index:
            oldpage = self.getPage(index)
            width = oldpage.mediaBox.getWidth()
            height = oldpage.mediaBox.getHeight()
        page = PageObject.createBlankPage(self, width, height)
        self.insertPage(page, index)
        return page

    def addJS(self, javascript):
        """
        Add Javascript which will launch upon opening this PDF.

        :param str javascript: Your Javascript.

        >>> output.addJS("this.print({bUI:true,bSilent:false,bShrinkToFit:true});")
        # Example: This will launch the print window when the PDF is opened.
        """
        js = DictionaryObject()
        js.update({
                NameObject("/Type"): NameObject("/Action"),
                NameObject("/S"): NameObject("/JavaScript"),
                NameObject("/JS"): NameObject("(%s)" % javascript)
                })
        js_indirect_object = self._addObject(js)

        # We need a name for parameterized javascript in the pdf file, but it can be anything.
        js_string_name = str(uuid.uuid4())

        js_name_tree = DictionaryObject()
        js_name_tree.update({
                NameObject("/JavaScript"): DictionaryObject({
                  NameObject("/Names"): ArrayObject([createStringObject(js_string_name), js_indirect_object])
                })
              })
        self._addObject(js_name_tree)

        self._root_object.update({
                NameObject("/OpenAction"): js_indirect_object,
                NameObject("/Names"): js_name_tree
                })

    def addAttachment(self, fname, fdata):
        """
        Embed a file inside the PDF.

        :param str fname: The filename to display.
        :param str fdata: The data in the file.
      
        Reference:
        https://www.adobe.com/content/dam/Adobe/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
        Section 7.11.3
        """
        
        # We need 3 entries:
        # * The file's data
        # * The /Filespec entry
        # * The file's name, which goes in the Catalog
        

        # The entry for the file
        """ Sample:
        8 0 obj
        <<
         /Length 12
         /Type /EmbeddedFile
        >>
        stream
        Hello world!
        endstream
        endobj        
        """
        file_entry = DecodedStreamObject()
        file_entry.setData(fdata)
        file_entry.update({
                NameObject("/Type"): NameObject("/EmbeddedFile")
                })

        # The Filespec entry
        """ Sample:
        7 0 obj
        <<
         /Type /Filespec
         /F (hello.txt)
         /EF << /F 8 0 R >>
        >>
        """
        efEntry = DictionaryObject()
        efEntry.update({ NameObject("/F"):file_entry })
        
        filespec = DictionaryObject()
        filespec.update({
                NameObject("/Type"): NameObject("/Filespec"),
                NameObject("/F"): createStringObject(fname),  # Perhaps also try TextStringObject
                NameObject("/EF"): efEntry
                })
                
        # Then create the entry for the root, as it needs a reference to the Filespec
        """ Sample:
        1 0 obj
        <<
         /Type /Catalog
         /Outlines 2 0 R
         /Pages 3 0 R
         /Names << /EmbeddedFiles << /Names [(hello.txt) 7 0 R] >> >>
        >>
        endobj
        
        """
        embeddedFilesNamesDictionary = DictionaryObject()
        embeddedFilesNamesDictionary.update({
                NameObject("/Names"): ArrayObject([createStringObject(fname), filespec])
                })
        
        embeddedFilesDictionary = DictionaryObject()
        embeddedFilesDictionary.update({
                NameObject("/EmbeddedFiles"): embeddedFilesNamesDictionary
                })
        # Update the root
        self._root_object.update({
                NameObject("/Names"): embeddedFilesDictionary
                })

    def appendPagesFromReader(self, reader, after_page_append=None):
        """
        Copy pages from reader to writer. Includes an optional callback parameter
        which is invoked after pages are appended to the writer.
        
        :param reader: a PdfFileReader object from which to copy page
            annotations to this writer object.  The writer's annots
        will then be updated
        :callback after_page_append (function): Callback function that is invoked after
            each page is appended to the writer. Callback signature:

            :param writer_pageref (PDF page reference): Reference to the page
                appended to the writer.
        """
        # Get page count from writer and reader
        reader_num_pages = reader.getNumPages()
        writer_num_pages = self.getNumPages()

        # Copy pages from reader to writer
        for rpagenum in range(0, reader_num_pages):
            reader_page = reader.getPage(rpagenum)
            self.addPage(reader_page)
            writer_page = self.getPage(writer_num_pages+rpagenum)
            # Trigger callback, pass writer page as parameter
            if callable(after_page_append): after_page_append(writer_page)

    def updatePageFormFieldValues(self, page, fields):
        '''
        Update the form field values for a given page from a fields dictionary.
        Copy field texts and values from fields to page.

        :param page: Page reference from PDF writer where the annotations
            and field data will be updated.
        :param fields: a Python dictionary of field names (/T) and text
            values (/V)
        '''
        # Iterate through pages, update field values
        for j in range(0, len(page['/Annots'])):
            writer_annot = page['/Annots'][j].getObject()
            for field in fields:
                if writer_annot.get('/T') == field:
                    writer_annot.update({
                        NameObject("/V"): TextStringObject(fields[field])
                    })

    def cloneReaderDocumentRoot(self, reader):
        '''
        Copy the reader document root to the writer.
        
        :param reader:  PdfFileReader from the document root should be copied.
        :callback after_page_append
        '''
        self._root_object = reader.trailer['/Root']

    def cloneDocumentFromReader(self, reader, after_page_append=None):
        '''
        Create a copy (clone) of a document from a PDF file reader

        :param reader: PDF file reader instance from which the clone
            should be created.
        :callback after_page_append (function): Callback function that is invoked after
            each page is appended to the writer. Signature includes a reference to the
            appended page (delegates to appendPagesFromReader). Callback signature:

            :param writer_pageref (PDF page reference): Reference to the page just
                appended to the document.
        '''
        self.cloneReaderDocumentRoot(reader)
        self.appendPagesFromReader(reader, after_page_append)

    def encrypt(self, user_pwd, owner_pwd = None, use_128bit = True):
        """
        Encrypt this PDF file with the PDF Standard encryption handler.

        :param str user_pwd: The "user password", which allows for opening
            and reading the PDF file with the restrictions provided.
        :param str owner_pwd: The "owner password", which allows for
            opening the PDF files without any restrictions.  By default,
            the owner password is the same as the user password.
        :param bool use_128bit: flag as to whether to use 128bit
            encryption.  When false, 40bit encryption will be used.  By default,
            this flag is on.
        """
        import time, random
        if owner_pwd == None:
            owner_pwd = user_pwd
        if use_128bit:
            V = 2
            rev = 3
            keylen = int(128 / 8)
        else:
            V = 1
            rev = 2
            keylen = int(40 / 8)
        # permit everything:
        P = -1
        O = ByteStringObject(_alg33(owner_pwd, user_pwd, rev, keylen))
        ID_1 = ByteStringObject(md5(b_(repr(time.time()))).digest())
        ID_2 = ByteStringObject(md5(b_(repr(random.random()))).digest())
        self._ID = ArrayObject((ID_1, ID_2))
        if rev == 2:
            U, key = _alg34(user_pwd, O, P, ID_1)
        else:
            assert rev == 3
            U, key = _alg35(user_pwd, rev, keylen, O, P, ID_1, False)
        encrypt = DictionaryObject()
        encrypt[NameObject("/Filter")] = NameObject("/Standard")
        encrypt[NameObject("/V")] = NumberObject(V)
        if V == 2:
            encrypt[NameObject("/Length")] = NumberObject(keylen * 8)
        encrypt[NameObject("/R")] = NumberObject(rev)
        encrypt[NameObject("/O")] = ByteStringObject(O)
        encrypt[NameObject("/U")] = ByteStringObject(U)
        encrypt[NameObject("/P")] = NumberObject(P)
        self._encrypt = self._addObject(encrypt)
        self._encrypt_key = key

    def write(self, stream):
        """
        Writes the collection of pages added to this object out as a PDF file.

        :param stream: An object to write the file to.  The object must support
            the write method and the tell method, similar to a file object.
        """
        if hasattr(stream, 'mode') and 'b' not in stream.mode:
            warnings.warn("File <%s> to write to is not in binary mode. It may not be written to correctly." % stream.name)
        debug = False
        import struct

        if not self._root:
            self._root = self._addObject(self._root_object)

        externalReferenceMap = {}

        # PDF objects sometimes have circular references to their /Page objects
        # inside their object tree (for example, annotations).  Those will be
        # indirect references to objects that we've recreated in this PDF.  To
        # address this problem, PageObject's store their original object
        # reference number, and we add it to the external reference map before
        # we sweep for indirect references.  This forces self-page-referencing
        # trees to reference the correct new object location, rather than
        # copying in a new copy of the page object.
        for objIndex in range(len(self._objects)):
            obj = self._objects[objIndex]
            if isinstance(obj, PageObject) and obj.indirectRef != None:
                data = obj.indirectRef
                if data.pdf not in externalReferenceMap:
                    externalReferenceMap[data.pdf] = {}
                if data.generation not in externalReferenceMap[data.pdf]:
                    externalReferenceMap[data.pdf][data.generation] = {}
                externalReferenceMap[data.pdf][data.generation][data.idnum] = IndirectObject(objIndex + 1, 0, self)

        self.stack = []
        if debug: print(("ERM:", externalReferenceMap, "root:", self._root))
        self._sweepIndirectReferences(externalReferenceMap, self._root)
        del self.stack

        # Begin writing:
        object_positions = []
        stream.write(self._header + b_("\n"))
        for i in range(len(self._objects)):
            idnum = (i + 1)
            obj = self._objects[i]
            object_positions.append(stream.tell())
            stream.write(b_(str(idnum) + " 0 obj\n"))
            key = None
            if hasattr(self, "_encrypt") and idnum != self._encrypt.idnum:
                pack1 = struct.pack("<i", i + 1)[:3]
                pack2 = struct.pack("<i", 0)[:2]
                key = self._encrypt_key + pack1 + pack2
                assert len(key) == (len(self._encrypt_key) + 5)
                md5_hash = md5(key).digest()
                key = md5_hash[:min(16, len(self._encrypt_key) + 5)]
            obj.writeToStream(stream, key)
            stream.write(b_("\nendobj\n"))

        # xref table
        xref_location = stream.tell()
        stream.write(b_("xref\n"))
        stream.write(b_("0 %s\n" % (len(self._objects) + 1)))
        stream.write(b_("%010d %05d f \n" % (0, 65535)))
        for offset in object_positions:
            stream.write(b_("%010d %05d n \n" % (offset, 0)))

        # trailer
        stream.write(b_("trailer\n"))
        trailer = DictionaryObject()
        trailer.update({
                NameObject("/Size"): NumberObject(len(self._objects) + 1),
                NameObject("/Root"): self._root,
                NameObject("/Info"): self._info,
                })
        if hasattr(self, "_ID"):
            trailer[NameObject("/ID")] = self._ID
        if hasattr(self, "_encrypt"):
            trailer[NameObject("/Encrypt")] = self._encrypt
        trailer.writeToStream(stream, None)

        # eof
        stream.write(b_("\nstartxref\n%s\n%%%%EOF\n" % (xref_location)))

    def addMetadata(self, infos):
        """
        Add custom metadata to the output.

        :param dict infos: a Python dictionary where each key is a field
            and each value is your new metadata.
        """
        args = {}
        for key, value in list(infos.items()):
            args[NameObject(key)] = createStringObject(value)
        self.getObject(self._info).update(args)

    def _sweepIndirectReferences(self, externMap, data):
        debug = False
        if debug: print((data, "TYPE", data.__class__.__name__))
        if isinstance(data, DictionaryObject):
            for key, value in list(data.items()):
                origvalue = value
                value = self._sweepIndirectReferences(externMap, value)
                if isinstance(value, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    value = self._addObject(value)
                data[key] = value
            return data
        elif isinstance(data, ArrayObject):
            for i in range(len(data)):
                value = self._sweepIndirectReferences(externMap, data[i])
                if isinstance(value, StreamObject):
                    # an array value is a stream.  streams must be indirect
                    # objects, so we need to change this value
                    value = self._addObject(value)
                data[i] = value
            return data
        elif isinstance(data, IndirectObject):
            # internal indirect references are fine
            if data.pdf == self:
                if data.idnum in self.stack:
                    return data
                else:
                    self.stack.append(data.idnum)
                    realdata = self.getObject(data)
                    self._sweepIndirectReferences(externMap, realdata)
                    return data
            else:
                newobj = externMap.get(data.pdf, {}).get(data.generation, {}).get(data.idnum, None)
                if newobj == None:
                    try:
                        newobj = data.pdf.getObject(data)
                        self._objects.append(None) # placeholder
                        idnum = len(self._objects)
                        newobj_ido = IndirectObject(idnum, 0, self)
                        if data.pdf not in externMap:
                            externMap[data.pdf] = {}
                        if data.generation not in externMap[data.pdf]:
                            externMap[data.pdf][data.generation] = {}
                        externMap[data.pdf][data.generation][data.idnum] = newobj_ido
                        newobj = self._sweepIndirectReferences(externMap, newobj)
                        self._objects[idnum-1] = newobj
                        return newobj_ido
                    except ValueError:
                        # Unable to resolve the Object, returning NullObject instead.
                        return NullObject()
                return newobj
        else:
            return data

    def getReference(self, obj):
        idnum = self._objects.index(obj) + 1
        ref = IndirectObject(idnum, 0, self)
        assert ref.getObject() == obj
        return ref

    def getOutlineRoot(self):
        if '/Outlines' in self._root_object:
            outline = self._root_object['/Outlines']
            idnum = self._objects.index(outline) + 1
            outlineRef = IndirectObject(idnum, 0, self)
            assert outlineRef.getObject() == outline
        else:
            outline = TreeObject()
            outline.update({ })
            outlineRef = self._addObject(outline)
            self._root_object[NameObject('/Outlines')] = outlineRef

        return outline

    def getNamedDestRoot(self):
        if '/Names' in self._root_object and isinstance(self._root_object['/Names'], DictionaryObject):
            names = self._root_object['/Names']
            idnum = self._objects.index(names) + 1
            namesRef = IndirectObject(idnum, 0, self)
            assert namesRef.getObject() == names
            if '/Dests' in names and isinstance(names['/Dests'], DictionaryObject):
                dests = names['/Dests']
                idnum = self._objects.index(dests) + 1
                destsRef = IndirectObject(idnum, 0, self)
                assert destsRef.getObject() == dests
                if '/Names' in dests:
                    nd = dests['/Names']
                else:
                    nd = ArrayObject()
                    dests[NameObject('/Names')] = nd
            else:
                dests = DictionaryObject()
                destsRef = self._addObject(dests)
                names[NameObject('/Dests')] = destsRef
                nd = ArrayObject()
                dests[NameObject('/Names')] = nd

        else:
            names = DictionaryObject()
            namesRef = self._addObject(names)
            self._root_object[NameObject('/Names')] = namesRef
            dests = DictionaryObject()
            destsRef = self._addObject(dests)
            names[NameObject('/Dests')] = destsRef
            nd = ArrayObject()
            dests[NameObject('/Names')] = nd

        return nd

    def addBookmarkDestination(self, dest, parent=None):
        destRef = self._addObject(dest)

        outlineRef = self.getOutlineRoot()

        if parent == None:
            parent = outlineRef

        parent = parent.getObject()
        #print parent.__class__.__name__
        parent.addChild(destRef, self)

        return destRef

    def addBookmarkDict(self, bookmark, parent=None):
        bookmarkObj = TreeObject()
        for k, v in list(bookmark.items()):
            bookmarkObj[NameObject(str(k))] = v
        bookmarkObj.update(bookmark)

        if '/A' in bookmark:
            action = DictionaryObject()
            for k, v in list(bookmark['/A'].items()):
                action[NameObject(str(k))] = v
            actionRef = self._addObject(action)
            bookmarkObj[NameObject('/A')] = actionRef

        bookmarkRef = self._addObject(bookmarkObj)

        outlineRef = self.getOutlineRoot()

        if parent == None:
            parent = outlineRef

        parent = parent.getObject()
        parent.addChild(bookmarkRef, self)

        return bookmarkRef

    def addBookmark(self, title, pagenum, parent=None, color=None, bold=False, italic=False, fit='/Fit', *args):
        """
        Add a bookmark to this PDF file.

        :param str title: Title to use for this bookmark.
        :param int pagenum: Page number this bookmark will point to.
        :param parent: A reference to a parent bookmark to create nested
            bookmarks.
        :param tuple color: Color of the bookmark as a red, green, blue tuple
            from 0.0 to 1.0
        :param bool bold: Bookmark is bold
        :param bool italic: Bookmark is italic
        :param str fit: The fit of the destination page. See
            :meth:`addLink()<addLink>` for details.
        """
        pageRef = self.getObject(self._pages)['/Kids'][pagenum]
        action = DictionaryObject()
        zoomArgs = []
        for a in args:
            if a is not None:
                zoomArgs.append(NumberObject(a))
            else:
                zoomArgs.append(NullObject())
        dest = Destination(NameObject("/"+title + " bookmark"), pageRef, NameObject(fit), *zoomArgs)
        destArray = dest.getDestArray()
        action.update({
            NameObject('/D') : destArray,
            NameObject('/S') : NameObject('/GoTo')
        })
        actionRef = self._addObject(action)

        outlineRef = self.getOutlineRoot()

        if parent == None:
            parent = outlineRef

        bookmark = TreeObject()

        bookmark.update({
            NameObject('/A'): actionRef,
            NameObject('/Title'): createStringObject(title),
        })

        if color is not None:
            bookmark.update({NameObject('/C'): ArrayObject([FloatObject(c) for c in color])})

        format = 0
        if italic:
            format += 1
        if bold:
            format += 2
        if format:
            bookmark.update({NameObject('/F'): NumberObject(format)})

        bookmarkRef = self._addObject(bookmark)

        parent = parent.getObject()
        parent.addChild(bookmarkRef, self)

        return bookmarkRef

    def addNamedDestinationObject(self, dest):
        destRef = self._addObject(dest)

        nd = self.getNamedDestRoot()
        nd.extend([dest['/Title'], destRef])

        return destRef

    def addNamedDestination(self, title, pagenum):
        pageRef = self.getObject(self._pages)['/Kids'][pagenum]
        dest = DictionaryObject()
        dest.update({
            NameObject('/D') : ArrayObject([pageRef, NameObject('/FitH'), NumberObject(826)]),
            NameObject('/S') : NameObject('/GoTo')
        })

        destRef = self._addObject(dest)
        nd = self.getNamedDestRoot()

        nd.extend([title, destRef])

        return destRef

    def removeLinks(self):
        """
        Removes links and annotations from this output.
        """
        pages = self.getObject(self._pages)['/Kids']
        for page in pages:
            pageRef = self.getObject(page)
            if "/Annots" in pageRef:
                del pageRef['/Annots']

    def removeImages(self, ignoreByteStringObject=False):
        """
        Removes images from this output.

        :param bool ignoreByteStringObject: optional parameter
            to ignore ByteString Objects.
        """
        pages = self.getObject(self._pages)['/Kids']
        for j in range(len(pages)):
            page = pages[j]
            pageRef = self.getObject(page)
            content = pageRef['/Contents'].getObject()
            if not isinstance(content, ContentStream):
                content = ContentStream(content, pageRef)

            _operations = []
            seq_graphics = False
            for operands, operator in content.operations:
                if operator == b_('Tj'):
                    text = operands[0]
                    if ignoreByteStringObject:
                        if not isinstance(text, TextStringObject):
                            operands[0] = TextStringObject()
                elif operator == b_("'"):
                    text = operands[0]
                    if ignoreByteStringObject:
                        if not isinstance(text, TextStringObject):
                            operands[0] = TextStringObject()
                elif operator == b_('"'):
                    text = operands[2]
                    if ignoreByteStringObject:
                        if not isinstance(text, TextStringObject):
                            operands[2] = TextStringObject()
                elif operator == b_("TJ"):
                    for i in range(len(operands[0])):
                        if ignoreByteStringObject:
                            if not isinstance(operands[0][i], TextStringObject):
                                operands[0][i] = TextStringObject()

                if operator == b_('q'):
                    seq_graphics = True
                if operator == b_('Q'):
                    seq_graphics = False
                if seq_graphics:
                    if operator in [b_('cm'), b_('w'), b_('J'), b_('j'), b_('M'), b_('d'), b_('ri'), b_('i'),
                            b_('gs'), b_('W'), b_('b'), b_('s'), b_('S'), b_('f'), b_('F'), b_('n'), b_('m'), b_('l'),
                            b_('c'), b_('v'), b_('y'), b_('h'), b_('B'), b_('Do'), b_('sh')]:
                        continue
                if operator == b_('re'):
                    continue
                _operations.append((operands, operator))

            content.operations = _operations
            pageRef.__setitem__(NameObject('/Contents'), content)

    def removeText(self, ignoreByteStringObject=False):
        """
        Removes images from this output.

        :param bool ignoreByteStringObject: optional parameter
            to ignore ByteString Objects.
        """
        pages = self.getObject(self._pages)['/Kids']
        for j in range(len(pages)):
            page = pages[j]
            pageRef = self.getObject(page)
            content = pageRef['/Contents'].getObject()
            if not isinstance(content, ContentStream):
                content = ContentStream(content, pageRef)
            for operands,operator in content.operations:
                if operator == b_('Tj'):
                    text = operands[0]
                    if not ignoreByteStringObject:
                        if isinstance(text, TextStringObject):
                            operands[0] = TextStringObject()
                    else:
                        if isinstance(text, TextStringObject) or \
                                isinstance(text, ByteStringObject):
                            operands[0] = TextStringObject()
                elif operator == b_("'"):
                    text = operands[0]
                    if not ignoreByteStringObject:
                        if isinstance(text, TextStringObject):
                            operands[0] = TextStringObject()
                    else:
                        if isinstance(text, TextStringObject) or \
                                isinstance(text, ByteStringObject):
                            operands[0] = TextStringObject()
                elif operator == b_('"'):
                    text = operands[2]
                    if not ignoreByteStringObject:
                        if isinstance(text, TextStringObject):
                            operands[2] = TextStringObject()
                    else:
                        if isinstance(text, TextStringObject) or \
                                isinstance(text, ByteStringObject):
                            operands[2] = TextStringObject()
                elif operator == b_("TJ"):
                    for i in range(len(operands[0])):
                        if not ignoreByteStringObject:
                            if isinstance(operands[0][i], TextStringObject):
                                operands[0][i] = TextStringObject()
                        else:
                            if isinstance(operands[0][i], TextStringObject) or \
                                    isinstance(operands[0][i], ByteStringObject):
                                operands[0][i] = TextStringObject()

            pageRef.__setitem__(NameObject('/Contents'), content)

    def addLink(self, pagenum, pagedest, rect, border=None, fit='/Fit', *args):
        """
        Add an internal link from a rectangular area to the specified page.

        :param int pagenum: index of the page on which to place the link.
        :param int pagedest: index of the page to which the link should go.
        :param rect: :class:`RectangleObject<PyPDF2.generic.RectangleObject>` or array of four
            integers specifying the clickable rectangular area
            ``[xLL, yLL, xUR, yUR]``, or string in the form ``"[ xLL yLL xUR yUR ]"``.
        :param border: if provided, an array describing border-drawing
            properties. See the PDF spec for details. No border will be
            drawn if this argument is omitted.
        :param str fit: Page fit or 'zoom' option (see below). Additional arguments may need
            to be supplied. Passing ``None`` will be read as a null value for that coordinate.

        Valid zoom arguments (see Table 8.2 of the PDF 1.7 reference for details):
             /Fit       No additional arguments
             /XYZ       [left] [top] [zoomFactor]
             /FitH      [top]
             /FitV      [left]
             /FitR      [left] [bottom] [right] [top]
             /FitB      No additional arguments
             /FitBH     [top]
             /FitBV     [left]
        """

        pageLink = self.getObject(self._pages)['/Kids'][pagenum]
        pageDest = self.getObject(self._pages)['/Kids'][pagedest] #TODO: switch for external link
        pageRef = self.getObject(pageLink)

        if border is not None:
            borderArr = [NameObject(n) for n in border[:3]]
            if len(border) == 4:
                dashPattern = ArrayObject([NameObject(n) for n in border[3]])
                borderArr.append(dashPattern)
        else:
            borderArr = [NumberObject(0)] * 3

        if isString(rect):
            rect = NameObject(rect)
        elif isinstance(rect, RectangleObject):
            pass
        else:
            rect = RectangleObject(rect)

        zoomArgs = []
        for a in args:
            if a is not None:
                zoomArgs.append(NumberObject(a))
            else:
                zoomArgs.append(NullObject())
        dest = Destination(NameObject("/LinkName"), pageDest, NameObject(fit), *zoomArgs) #TODO: create a better name for the link
        destArray = dest.getDestArray()

        lnk = DictionaryObject()
        lnk.update({
            NameObject('/Type'): NameObject('/Annot'),
            NameObject('/Subtype'): NameObject('/Link'),
            NameObject('/P'): pageLink,
            NameObject('/Rect'): rect,
            NameObject('/Border'): ArrayObject(borderArr),
            NameObject('/Dest'): destArray
        })
        lnkRef = self._addObject(lnk)

        if "/Annots" in pageRef:
            pageRef['/Annots'].append(lnkRef)
        else:
            pageRef[NameObject('/Annots')] = ArrayObject([lnkRef])

    _valid_layouts = ['/NoLayout', '/SinglePage', '/OneColumn', '/TwoColumnLeft', '/TwoColumnRight', '/TwoPageLeft', '/TwoPageRight']

    def getPageLayout(self):
        """
        Get the page layout.
        See :meth:`setPageLayout()<PdfFileWriter.setPageLayout>` for a description of valid layouts.

        :return: Page layout currently being used.
        :rtype: str, None if not specified
        """
        try:
            return self._root_object['/PageLayout']
        except KeyError:
            return None

    def setPageLayout(self, layout):
        """
        Set the page layout

        :param str layout: The page layout to be used

        Valid layouts are:
             /NoLayout        Layout explicitly not specified
             /SinglePage      Show one page at a time
             /OneColumn       Show one column at a time
             /TwoColumnLeft   Show pages in two columns, odd-numbered pages on the left
             /TwoColumnRight  Show pages in two columns, odd-numbered pages on the right
             /TwoPageLeft     Show two pages at a time, odd-numbered pages on the left
             /TwoPageRight    Show two pages at a time, odd-numbered pages on the right
        """
        if not isinstance(layout, NameObject):
            if layout not in self._valid_layouts:
                warnings.warn("Layout should be one of: {}".format(', '.join(self._valid_layouts)))
            layout = NameObject(layout)
        self._root_object.update({NameObject('/PageLayout'): layout})

    pageLayout = property(getPageLayout, setPageLayout)
    """Read and write property accessing the :meth:`getPageLayout()<PdfFileWriter.getPageLayout>`
    and :meth:`setPageLayout()<PdfFileWriter.setPageLayout>` methods."""

    _valid_modes = ['/UseNone', '/UseOutlines', '/UseThumbs', '/FullScreen', '/UseOC', '/UseAttachments']

    def getPageMode(self):
        """
        Get the page mode.
        See :meth:`setPageMode()<PdfFileWriter.setPageMode>` for a description
        of valid modes.

        :return: Page mode currently being used.
        :rtype: str, None if not specified
        """
        try:
            return self._root_object['/PageMode']
        except KeyError:
            return None

    def setPageMode(self, mode):
        """
        Set the page mode.

        :param str mode: The page mode to use.

        Valid modes are:
            /UseNone         Do not show outlines or thumbnails panels
            /UseOutlines     Show outlines (aka bookmarks) panel
            /UseThumbs       Show page thumbnails panel
            /FullScreen      Fullscreen view
            /UseOC           Show Optional Content Group (OCG) panel
            /UseAttachments  Show attachments panel
        """
        if not isinstance(mode, NameObject):
            if mode not in self._valid_modes:
                warnings.warn("Mode should be one of: {}".format(', '.join(self._valid_modes)))
            mode = NameObject(mode)
        self._root_object.update({NameObject('/PageMode'): mode})

    pageMode = property(getPageMode, setPageMode)
    """Read and write property accessing the :meth:`getPageMode()<PdfFileWriter.getPageMode>`
    and :meth:`setPageMode()<PdfFileWriter.setPageMode>` methods."""


class PdfFileReader(object):
    """
    Initializes a PdfFileReader object.  This operation can take some time, as
    the PDF stream's cross-reference tables are read into memory.

    :param stream: A File object or an object that supports the standard read
        and seek methods similar to a File object. Could also be a
        string representing a path to a PDF file.
    :param bool strict: Determines whether user should be warned of all
        problems and also causes some correctable problems to be fatal.
        Defaults to ``True``.
    :param warndest: Destination for logging warnings (defaults to
        ``sys.stderr``).
    :param bool overwriteWarnings: Determines whether to override Python's
        ``warnings.py`` module with a custom implementation (defaults to
        ``True``).
    """
    def __init__(self, stream, strict=True, warndest = None, overwriteWarnings = True):
        if overwriteWarnings:
            # have to dynamically override the default showwarning since there are no
            # public methods that specify the 'file' parameter
            def _showwarning(message, category, filename, lineno, file=warndest, line=None):
                if file is None:
                    file = sys.stderr
                try:
                    file.write(formatWarning(message, category, filename, lineno, line))
                except IOError:
                    pass
            warnings.showwarning = _showwarning
        self.strict = strict
        self.flattenedPages = None
        self.resolvedObjects = {}
        self.xrefIndex = 0
        self._pageId2Num = None # map page IndirectRef number to Page Number
        if hasattr(stream, 'mode') and 'b' not in stream.mode:
            warnings.warn("PdfFileReader stream/file object is not in binary mode. It may not be read correctly.", utils.PdfReadWarning)
        if isString(stream):
            fileobj = open(stream, 'rb')
            stream = BytesIO(b_(fileobj.read()))
            fileobj.close()
        self.read(stream)
        self.stream = stream

        self._override_encryption = False

    def getDocumentInfo(self):
        """
        Retrieves the PDF file's document information dictionary, if it exists.
        Note that some PDF files use metadata streams instead of docinfo
        dictionaries, and these metadata streams will not be accessed by this
        function.

        :return: the document information of this PDF file
        :rtype: :class:`DocumentInformation<pdf.DocumentInformation>` or ``None`` if none exists.
        """
        if "/Info" not in self.trailer:
            return None
        obj = self.trailer['/Info']
        retval = DocumentInformation()
        retval.update(obj)
        return retval

    documentInfo = property(lambda self: self.getDocumentInfo(), None, None)
    """Read-only property that accesses the :meth:`getDocumentInfo()<PdfFileReader.getDocumentInfo>` function."""

    def getXmpMetadata(self):
        """
        Retrieves XMP (Extensible Metadata Platform) data from the PDF document
        root.

        :return: a :class:`XmpInformation<xmp.XmpInformation>`
            instance that can be used to access XMP metadata from the document.
        :rtype: :class:`XmpInformation<xmp.XmpInformation>` or
            ``None`` if no metadata was found on the document root.
        """
        try:
            self._override_encryption = True
            return self.trailer["/Root"].getXmpMetadata()
        finally:
            self._override_encryption = False

    xmpMetadata = property(lambda self: self.getXmpMetadata(), None, None)
    """
    Read-only property that accesses the
    :meth:`getXmpMetadata()<PdfFileReader.getXmpMetadata>` function.
    """

    def getNumPages(self):
        """
        Calculates the number of pages in this PDF file.

        :return: number of pages
        :rtype: int
        :raises PdfReadError: if file is encrypted and restrictions prevent
            this action.
        """

        # Flattened pages will not work on an Encrypted PDF;
        # the PDF file's page count is used in this case. Otherwise,
        # the original method (flattened page count) is used.
        if self.isEncrypted:
            try:
                self._override_encryption = True
                self.decrypt('')
                return self.trailer["/Root"]["/Pages"]["/Count"]
            except:
                raise utils.PdfReadError("File has not been decrypted")
            finally:
                self._override_encryption = False
        else:
            if self.flattenedPages == None:
                self._flatten()
            return len(self.flattenedPages)

    numPages = property(lambda self: self.getNumPages(), None, None)
    """
    Read-only property that accesses the
    :meth:`getNumPages()<PdfFileReader.getNumPages>` function.
    """

    def getPage(self, pageNumber):
        """
        Retrieves a page by number from this PDF file.

        :param int pageNumber: The page number to retrieve
            (pages begin at zero)
        :return: a :class:`PageObject<pdf.PageObject>` instance.
        :rtype: :class:`PageObject<pdf.PageObject>`
        """
        ## ensure that we're not trying to access an encrypted PDF
        #assert not self.trailer.has_key("/Encrypt")
        if self.flattenedPages == None:
            self._flatten()
        return self.flattenedPages[pageNumber]

    namedDestinations = property(lambda self:
                                  self.getNamedDestinations(), None, None)
    """
    Read-only property that accesses the
    :meth:`getNamedDestinations()<PdfFileReader.getNamedDestinations>` function.
    """

    # A select group of relevant field attributes. For the complete list,
    # see section 8.6.2 of the PDF 1.7 reference.

    def getFields(self, tree = None, retval = None, fileobj = None):
        """
        Extracts field data if this PDF contains interactive form fields.
        The *tree* and *retval* parameters are for recursive use.

        :param fileobj: A file object (usually a text file) to write
            a report to on all interactive form fields found.
        :return: A dictionary where each key is a field name, and each
            value is a :class:`Field<PyPDF2.generic.Field>` object. By
            default, the mapping name is used for keys.
        :rtype: dict, or ``None`` if form data could not be located.
        """
        fieldAttributes = {"/FT" : "Field Type", "/Parent" : "Parent",
                       "/T" : "Field Name", "/TU" : "Alternate Field Name",
                       "/TM" : "Mapping Name", "/Ff" : "Field Flags",
                       "/V" : "Value", "/DV" : "Default Value"}
        if retval == None:
            retval = {}
            catalog = self.trailer["/Root"]
            # get the AcroForm tree
            if "/AcroForm" in catalog:
                tree = catalog["/AcroForm"]
            else:
                return None
        if tree == None:
            return retval

        self._checkKids(tree, retval, fileobj)
        for attr in fieldAttributes:
            if attr in tree:
                # Tree is a field
                self._buildField(tree, retval, fileobj, fieldAttributes)
                break

        if "/Fields" in tree:
            fields = tree["/Fields"]
            for f in fields:
                field = f.getObject()
                self._buildField(field, retval, fileobj, fieldAttributes)

        return retval

    def _buildField(self, field, retval, fileobj, fieldAttributes):
        self._checkKids(field, retval, fileobj)
        try:
            key = field["/TM"]
        except KeyError:
            try:
                key = field["/T"]
            except KeyError:
                # Ignore no-name field for now
                return
        if fileobj:
            self._writeField(fileobj, field, fieldAttributes)
            fileobj.write("\n")
        retval[key] = Field(field)

    def _checkKids(self, tree, retval, fileobj):
        if "/Kids" in tree:
            # recurse down the tree
            for kid in tree["/Kids"]:
                self.getFields(kid.getObject(), retval, fileobj)

    def _writeField(self, fileobj, field, fieldAttributes):
        order = ["/TM", "/T", "/FT", "/Parent", "/TU", "/Ff", "/V", "/DV"]
        for attr in order:
            attrName = fieldAttributes[attr]
            try:
                if attr == "/FT":
                    # Make the field type value more clear
                    types = {"/Btn":"Button", "/Tx":"Text", "/Ch": "Choice",
                             "/Sig":"Signature"}
                    if field[attr] in types:
                        fileobj.write(attrName + ": " + types[field[attr]] + "\n")
                elif attr == "/Parent":
                    # Let's just write the name of the parent
                    try:
                        name = field["/Parent"]["/TM"]
                    except KeyError:
                        name = field["/Parent"]["/T"]
                    fileobj.write(attrName + ": " + name + "\n")
                else:
                    fileobj.write(attrName + ": " + str(field[attr]) + "\n")
            except KeyError:
                # Field attribute is N/A or unknown, so don't write anything
                pass

    def getFormTextFields(self):
        ''' Retrieves form fields from the document with textual data (inputs, dropdowns)
        '''
        # Retrieve document form fields
        formfields = self.getFields()
        return dict(
            (formfields[field]['/T'], formfields[field].get('/V')) for field in formfields \
                if formfields[field].get('/FT') == '/Tx'
        )

    def getNamedDestinations(self, tree=None, retval=None):
        """
        Retrieves the named destinations present in the document.

        :return: a dictionary which maps names to
            :class:`Destinations<PyPDF2.generic.Destination>`.
        :rtype: dict
        """
        if retval == None:
            retval = {}
            catalog = self.trailer["/Root"]

            # get the name tree
            if "/Dests" in catalog:
                tree = catalog["/Dests"]
            elif "/Names" in catalog:
                names = catalog['/Names']
                if "/Dests" in names:
                    tree = names['/Dests']

        if tree == None:
            return retval

        if "/Kids" in tree:
            # recurse down the tree
            for kid in tree["/Kids"]:
                self.getNamedDestinations(kid.getObject(), retval)

        if "/Names" in tree:
            names = tree["/Names"]
            for i in range(0, len(names), 2):
                key = names[i].getObject()
                val = names[i+1].getObject()
                if isinstance(val, DictionaryObject) and '/D' in val:
                    val = val['/D']
                dest = self._buildDestination(key, val)
                if dest != None:
                    retval[key] = dest

        return retval

    outlines = property(lambda self: self.getOutlines(), None, None)
    """
    Read-only property that accesses the
        :meth:`getOutlines()<PdfFileReader.getOutlines>` function.
    """

    def getOutlines(self, node=None, outlines=None):
        """
        Retrieves the document outline present in the document.

        :return: a nested list of :class:`Destinations<PyPDF2.generic.Destination>`.
        """
        if outlines == None:
            outlines = []
            catalog = self.trailer["/Root"]

            # get the outline dictionary and named destinations
            if "/Outlines" in catalog:
                try:
                    lines = catalog["/Outlines"]
                except utils.PdfReadError:
                    # this occurs if the /Outlines object reference is incorrect
                    # for an example of such a file, see https://unglueit-files.s3.amazonaws.com/ebf/7552c42e9280b4476e59e77acc0bc812.pdf
                    # so continue to load the file without the Bookmarks
                    return outlines

                if "/First" in lines:
                    node = lines["/First"]
            self._namedDests = self.getNamedDestinations()

        if node == None:
          return outlines

        # see if there are any more outlines
        while True:
            outline = self._buildOutline(node)
            if outline:
                outlines.append(outline)

            # check for sub-outlines
            if "/First" in node:
                subOutlines = []
                self.getOutlines(node["/First"], subOutlines)
                if subOutlines:
                    outlines.append(subOutlines)

            if "/Next" not in node:
                break
            node = node["/Next"]

        return outlines

    def _getPageNumberByIndirect(self, indirectRef):
        """Generate _pageId2Num"""
        if self._pageId2Num is None:
            id2num = {}
            for i, x in enumerate(self.pages):
                id2num[x.indirectRef.idnum] = i
            self._pageId2Num = id2num

        if isinstance(indirectRef, int):
            idnum = indirectRef
        else:
            idnum = indirectRef.idnum

        ret = self._pageId2Num.get(idnum, -1)
        return ret

    def getPageNumber(self, page):
        """
        Retrieve page number of a given PageObject

        :param PageObject page: The page to get page number. Should be
            an instance of :class:`PageObject<PyPDF2.pdf.PageObject>`
        :return: the page number or -1 if page not found
        :rtype: int
        """
        indirectRef = page.indirectRef
        ret = self._getPageNumberByIndirect(indirectRef)
        return ret

    def getDestinationPageNumber(self, destination):
        """
        Retrieve page number of a given Destination object

        :param Destination destination: The destination to get page number.
             Should be an instance of
             :class:`Destination<PyPDF2.pdf.Destination>`
        :return: the page number or -1 if page not found
        :rtype: int
        """
        indirectRef = destination.page
        ret = self._getPageNumberByIndirect(indirectRef)
        return ret

    def _buildDestination(self, title, array):
        page, typ = array[0:2]
        array = array[2:]
        return Destination(title, page, typ, *array)

    def _buildOutline(self, node):
        dest, title, outline = None, None, None

        if "/A" in node and "/Title" in node:
            # Action, section 8.5 (only type GoTo supported)
            title  = node["/Title"]
            action = node["/A"]
            if action["/S"] == "/GoTo":
                dest = action["/D"]
        elif "/Dest" in node and "/Title" in node:
            # Destination, section 8.2.1
            title = node["/Title"]
            dest  = node["/Dest"]

        # if destination found, then create outline
        if dest:
            if isinstance(dest, ArrayObject):
                outline = self._buildDestination(title, dest)
            elif isString(dest) and dest in self._namedDests:
                outline = self._namedDests[dest]
                outline[NameObject("/Title")] = title
            else:
                raise utils.PdfReadError("Unexpected destination %r" % dest)
        return outline

    pages = property(lambda self: ConvertFunctionsToVirtualList(self.getNumPages, self.getPage),
        None, None)
    """
    Read-only property that emulates a list based upon the
    :meth:`getNumPages()<PdfFileReader.getNumPages>` and
    :meth:`getPage()<PdfFileReader.getPage>` methods.
    """

    def getPageLayout(self):
        """
        Get the page layout.
        See :meth:`setPageLayout()<PdfFileWriter.setPageLayout>`
        for a description of valid layouts.

        :return: Page layout currently being used.
        :rtype: ``str``, ``None`` if not specified
        """
        try:
            return self.trailer['/Root']['/PageLayout']
        except KeyError:
            return None

    pageLayout = property(getPageLayout)
    """Read-only property accessing the
    :meth:`getPageLayout()<PdfFileReader.getPageLayout>` method."""

    def getPageMode(self):
        """
        Get the page mode.
        See :meth:`setPageMode()<PdfFileWriter.setPageMode>`
        for a description of valid modes.

        :return: Page mode currently being used.
        :rtype: ``str``, ``None`` if not specified
        """
        try:
            return self.trailer['/Root']['/PageMode']
        except KeyError:
            return None

    pageMode = property(getPageMode)
    """Read-only property accessing the
    :meth:`getPageMode()<PdfFileReader.getPageMode>` method."""

    def _flatten(self, pages=None, inherit=None, indirectRef=None):
        inheritablePageAttributes = (
            NameObject("/Resources"), NameObject("/MediaBox"),
            NameObject("/CropBox"), NameObject("/Rotate")
            )
        if inherit == None:
            inherit = dict()
        if pages == None:
            self.flattenedPages = []
            catalog = self.trailer["/Root"].getObject()
            pages = catalog["/Pages"].getObject()

        t = "/Pages"
        if "/Type" in pages:
            t = pages["/Type"]

        if t == "/Pages":
            for attr in inheritablePageAttributes:
                if attr in pages:
                    inherit[attr] = pages[attr]
            for page in pages["/Kids"]:
                addt = {}
                if isinstance(page, IndirectObject):
                    addt["indirectRef"] = page
                self._flatten(page.getObject(), inherit, **addt)
        elif t == "/Page":
            for attr, value in list(inherit.items()):
                # if the page has it's own value, it does not inherit the
                # parent's value:
                if attr not in pages:
                    pages[attr] = value
            pageObj = PageObject(self, indirectRef)
            pageObj.update(pages)
            self.flattenedPages.append(pageObj)

    def _getObjectFromStream(self, indirectReference):
        # indirect reference to object in object stream
        # read the entire object stream into memory
        debug = False
        stmnum, idx = self.xref_objStm[indirectReference.idnum]
        if debug: print(("Here1: %s %s"%(stmnum, idx)))
        objStm = IndirectObject(stmnum, 0, self).getObject()
        if debug: print(("Here2: objStm=%s.. stmnum=%s data=%s"%(objStm, stmnum, objStm.getData())))
        # This is an xref to a stream, so its type better be a stream
        assert objStm['/Type'] == '/ObjStm'
        # /N is the number of indirect objects in the stream
        assert idx < objStm['/N']
        streamData = BytesIO(b_(objStm.getData()))
        for i in range(objStm['/N']):
            readNonWhitespace(streamData)
            streamData.seek(-1, 1)
            objnum = NumberObject.readFromStream(streamData)
            readNonWhitespace(streamData)
            streamData.seek(-1, 1)
            offset = NumberObject.readFromStream(streamData)
            readNonWhitespace(streamData)
            streamData.seek(-1, 1)
            if objnum != indirectReference.idnum:
                # We're only interested in one object
                continue
            if self.strict and idx != i:
                raise utils.PdfReadError("Object is in wrong index.")
            streamData.seek(objStm['/First']+offset, 0)
            if debug:
                pos = streamData.tell()
                streamData.seek(0, 0)
                lines = streamData.readlines()
                for i in range(0, len(lines)):
                    print((lines[i]))
                streamData.seek(pos, 0)
            try:
                obj = readObject(streamData, self)
            except utils.PdfStreamError as e:
                # Stream object cannot be read. Normally, a critical error, but
                # Adobe Reader doesn't complain, so continue (in strict mode?)
                e = sys.exc_info()[1]
                warnings.warn("Invalid stream (index %d) within object %d %d: %s" % \
                      (i, indirectReference.idnum, indirectReference.generation, e), utils.PdfReadWarning)

                if self.strict:
                    raise utils.PdfReadError("Can't read object stream: %s"%e)
                # Replace with null. Hopefully it's nothing important.
                obj = NullObject()
            return obj

        if self.strict: raise utils.PdfReadError("This is a fatal error in strict mode.")
        return NullObject()

    def getObject(self, indirectReference):
        debug = False
        if debug: print(("looking at:", indirectReference.idnum, indirectReference.generation))
        retval = self.cacheGetIndirectObject(indirectReference.generation,
                                                indirectReference.idnum)
        if retval != None:
            return retval
        if indirectReference.generation == 0 and \
                        indirectReference.idnum in self.xref_objStm:
            retval = self._getObjectFromStream(indirectReference)
        elif indirectReference.generation in self.xref and \
                indirectReference.idnum in self.xref[indirectReference.generation]:
            start = self.xref[indirectReference.generation][indirectReference.idnum]
            if debug: print(("  Uncompressed Object", indirectReference.idnum, indirectReference.generation, ":", start))
            self.stream.seek(start, 0)
            idnum, generation = self.readObjectHeader(self.stream)
            if idnum != indirectReference.idnum and self.xrefIndex:
                # Xref table probably had bad indexes due to not being zero-indexed
                if self.strict:
                    raise utils.PdfReadError("Expected object ID (%d %d) does not match actual (%d %d); xref table not zero-indexed." \
                                     % (indirectReference.idnum, indirectReference.generation, idnum, generation))
                else: pass # xref table is corrected in non-strict mode
            elif idnum != indirectReference.idnum:
                # some other problem
                raise utils.PdfReadError("Expected object ID (%d %d) does not match actual (%d %d)." \
                                         % (indirectReference.idnum, indirectReference.generation, idnum, generation))
            assert generation == indirectReference.generation
            retval = readObject(self.stream, self)

            # override encryption is used for the /Encrypt dictionary
            if not self._override_encryption and self.isEncrypted:
                # if we don't have the encryption key:
                if not hasattr(self, '_decryption_key'):
                    raise utils.PdfReadError("file has not been decrypted")
                # otherwise, decrypt here...
                import struct
                pack1 = struct.pack("<i", indirectReference.idnum)[:3]
                pack2 = struct.pack("<i", indirectReference.generation)[:2]
                key = self._decryption_key + pack1 + pack2
                assert len(key) == (len(self._decryption_key) + 5)
                md5_hash = md5(key).digest()
                key = md5_hash[:min(16, len(self._decryption_key) + 5)]
                retval = self._decryptObject(retval, key)
        else:
            warnings.warn("Object %d %d not defined."%(indirectReference.idnum,
                        indirectReference.generation), utils.PdfReadWarning)
            #if self.strict:
            raise utils.PdfReadError("Could not find object.")
        self.cacheIndirectObject(indirectReference.generation,
                    indirectReference.idnum, retval)
        return retval

    def _decryptObject(self, obj, key):
        if isinstance(obj, ByteStringObject) or isinstance(obj, TextStringObject):
            obj = createStringObject(utils.RC4_encrypt(key, obj.original_bytes))
        elif isinstance(obj, StreamObject):
            obj._data = utils.RC4_encrypt(key, obj._data)
        elif isinstance(obj, DictionaryObject):
            for dictkey, value in list(obj.items()):
                obj[dictkey] = self._decryptObject(value, key)
        elif isinstance(obj, ArrayObject):
            for i in range(len(obj)):
                obj[i] = self._decryptObject(obj[i], key)
        return obj

    def readObjectHeader(self, stream):
        # Should never be necessary to read out whitespace, since the
        # cross-reference table should put us in the right spot to read the
        # object header.  In reality... some files have stupid cross reference
        # tables that are off by whitespace bytes.
        extra = False
        utils.skipOverComment(stream)
        extra |= utils.skipOverWhitespace(stream); stream.seek(-1, 1)
        idnum = readUntilWhitespace(stream)
        extra |= utils.skipOverWhitespace(stream); stream.seek(-1, 1)
        generation = readUntilWhitespace(stream)
        obj = stream.read(3)
        readNonWhitespace(stream)
        stream.seek(-1, 1)
        if (extra and self.strict):
            #not a fatal error
            warnings.warn("Superfluous whitespace found in object header %s %s" % \
                          (idnum, generation), utils.PdfReadWarning)
        return int(idnum), int(generation)

    def cacheGetIndirectObject(self, generation, idnum):
        debug = False
        out = self.resolvedObjects.get((generation, idnum))
        if debug and out: print(("cache hit: %d %d"%(idnum, generation)))
        elif debug: print(("cache miss: %d %d"%(idnum, generation)))
        return out

    def cacheIndirectObject(self, generation, idnum, obj):
        # return None # Sometimes we want to turn off cache for debugging.
        if (generation, idnum) in self.resolvedObjects:
            msg = "Overwriting cache for %s %s"%(generation, idnum)
            if self.strict: raise utils.PdfReadError(msg)
            else:           warnings.warn(msg)
        self.resolvedObjects[(generation, idnum)] = obj
        return obj

    def read(self, stream):
        debug = False
        if debug: print(">>read", stream)
        # start at the end:
        stream.seek(-1, 2)
        if not stream.tell():
            raise utils.PdfReadError('Cannot read an empty file')
        last1K = stream.tell() - 1024 + 1 # offset of last 1024 bytes of stream
        line = b_('')
        while line[:5] != b_("%%EOF"):
            if stream.tell() < last1K:
                raise utils.PdfReadError("EOF marker not found")
            line = self.readNextEndLine(stream)
            if debug: print("  line:",line)

        # find startxref entry - the location of the xref table
        line = self.readNextEndLine(stream)
        try:
            startxref = int(line)
        except ValueError:
            # 'startxref' may be on the same line as the location
            if not line.startswith(b_("startxref")):
                raise utils.PdfReadError("startxref not found")
            startxref = int(line[9:].strip())
            warnings.warn("startxref on same line as offset")
        else:
            line = self.readNextEndLine(stream)
            if line[:9] != b_("startxref"):
                raise utils.PdfReadError("startxref not found")

        # read all cross reference tables and their trailers
        self.xref = {}
        self.xref_objStm = {}
        self.trailer = DictionaryObject()
        while True:
            # load the xref table
            stream.seek(startxref, 0)
            x = stream.read(1)
            if x == b_("x"):
                # standard cross-reference table
                ref = stream.read(4)
                if ref[:3] != b_("ref"):
                    raise utils.PdfReadError("xref table read error")
                readNonWhitespace(stream)
                stream.seek(-1, 1)
                firsttime = True; # check if the first time looking at the xref table
                while True:
                    num = readObject(stream, self)
                    if firsttime and num != 0:
                         self.xrefIndex = num
                         if self.strict:
                            warnings.warn("Xref table not zero-indexed. ID numbers for objects will be corrected.", utils.PdfReadWarning)
                            #if table not zero indexed, could be due to error from when PDF was created
                            #which will lead to mismatched indices later on, only warned and corrected if self.strict=True
                    firsttime = False
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    size = readObject(stream, self)
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    cnt = 0
                    while cnt < size:
                        line = stream.read(20)

                        # It's very clear in section 3.4.3 of the PDF spec
                        # that all cross-reference table lines are a fixed
                        # 20 bytes (as of PDF 1.7). However, some files have
                        # 21-byte entries (or more) due to the use of \r\n
                        # (CRLF) EOL's. Detect that case, and adjust the line
                        # until it does not begin with a \r (CR) or \n (LF).
                        while line[0] in b_("\x0D\x0A"):
                            stream.seek(-20 + 1, 1)
                            line = stream.read(20)

                        # On the other hand, some malformed PDF files
                        # use a single character EOL without a preceeding
                        # space.  Detect that case, and seek the stream
                        # back one character.  (0-9 means we've bled into
                        # the next xref entry, t means we've bled into the
                        # text "trailer"):
                        if line[-1] in b_("0123456789t"):
                            stream.seek(-1, 1)

                        offset, generation = line[:16].split(b_(" "))
                        offset, generation = int(offset), int(generation)
                        if generation not in self.xref:
                            self.xref[generation] = {}
                        if num in self.xref[generation]:
                            # It really seems like we should allow the last
                            # xref table in the file to override previous
                            # ones. Since we read the file backwards, assume
                            # any existing key is already set correctly.
                            pass
                        else:
                            self.xref[generation][num] = offset
                        cnt += 1
                        num += 1
                    readNonWhitespace(stream)
                    stream.seek(-1, 1)
                    trailertag = stream.read(7)
                    if trailertag != b_("trailer"):
                        # more xrefs!
                        stream.seek(-7, 1)
                    else:
                        break
                readNonWhitespace(stream)
                stream.seek(-1, 1)
                newTrailer = readObject(stream, self)
                for key, value in list(newTrailer.items()):
                    if key not in self.trailer:
                        self.trailer[key] = value
                if "/Prev" in newTrailer:
                    startxref = newTrailer["/Prev"]
                else:
                    break
            elif x.isdigit():
                # PDF 1.5+ Cross-Reference Stream
                stream.seek(-1, 1)
                idnum, generation = self.readObjectHeader(stream)
                xrefstream = readObject(stream, self)
                assert xrefstream["/Type"] == "/XRef"
                self.cacheIndirectObject(generation, idnum, xrefstream)
                streamData = BytesIO(b_(xrefstream.getData()))
                # Index pairs specify the subsections in the dictionary. If
                # none create one subsection that spans everything.
                idx_pairs = xrefstream.get("/Index", [0, xrefstream.get("/Size")])
                if debug: print(("read idx_pairs=%s"%list(self._pairs(idx_pairs))))
                entrySizes = xrefstream.get("/W")
                assert len(entrySizes) >= 3
                if self.strict and len(entrySizes) > 3:
                    raise utils.PdfReadError("Too many entry sizes: %s" %entrySizes)

                def getEntry(i):
                    # Reads the correct number of bytes for each entry. See the
                    # discussion of the W parameter in PDF spec table 17.
                    if entrySizes[i] > 0:
                        d = streamData.read(entrySizes[i])
                        return convertToInt(d, entrySizes[i])

                    # PDF Spec Table 17: A value of zero for an element in the
                    # W array indicates...the default value shall be used
                    if i == 0:  return 1 # First value defaults to 1
                    else:       return 0

                def used_before(num, generation):
                    # We move backwards through the xrefs, don't replace any.
                    return num in self.xref.get(generation, []) or \
                            num in self.xref_objStm

                # Iterate through each subsection
                last_end = 0
                for start, size in self._pairs(idx_pairs):
                    # The subsections must increase
                    assert start >= last_end
                    last_end = start + size
                    for num in range(start, start+size):
                        # The first entry is the type
                        xref_type = getEntry(0)
                        # The rest of the elements depend on the xref_type
                        if xref_type == 0:
                            # linked list of free objects
                            next_free_object = getEntry(1)
                            next_generation = getEntry(2)
                        elif xref_type == 1:
                            # objects that are in use but are not compressed
                            byte_offset = getEntry(1)
                            generation = getEntry(2)
                            if generation not in self.xref:
                                self.xref[generation] = {}
                            if not used_before(num, generation):
                                self.xref[generation][num] = byte_offset
                                if debug: print(("XREF Uncompressed: %s %s"%(
                                                num, generation)))
                        elif xref_type == 2:
                            # compressed objects
                            objstr_num = getEntry(1)
                            obstr_idx = getEntry(2)
                            generation = 0 # PDF spec table 18, generation is 0
                            if not used_before(num, generation):
                                if debug: print(("XREF Compressed: %s %s %s"%(
                                        num, objstr_num, obstr_idx)))
                                self.xref_objStm[num] = (objstr_num, obstr_idx)
                        elif self.strict:
                            raise utils.PdfReadError("Unknown xref type: %s"%
                                                        xref_type)

                trailerKeys = "/Root", "/Encrypt", "/Info", "/ID"
                for key in trailerKeys:
                    if key in xrefstream and key not in self.trailer:
                        self.trailer[NameObject(key)] = xrefstream.raw_get(key)
                if "/Prev" in xrefstream:
                    startxref = xrefstream["/Prev"]
                else:
                    break
            else:
                # bad xref character at startxref.  Let's see if we can find
                # the xref table nearby, as we've observed this error with an
                # off-by-one before.
                stream.seek(-11, 1)
                tmp = stream.read(20)
                xref_loc = tmp.find(b_("xref"))
                if xref_loc != -1:
                    startxref -= (10 - xref_loc)
                    continue
                # No explicit xref table, try finding a cross-reference stream.
                stream.seek(startxref, 0)
                found = False
                for look in range(5):
                    if stream.read(1).isdigit():
                        # This is not a standard PDF, consider adding a warning
                        startxref += look
                        found = True
                        break
                if found:
                    continue
                # no xref table found at specified location
                raise utils.PdfReadError("Could not find xref table at specified location")
        #if not zero-indexed, verify that the table is correct; change it if necessary
        if self.xrefIndex and not self.strict:
            loc = stream.tell()
            for gen in self.xref:
                if gen == 65535: continue
                for id in self.xref[gen]:
                    stream.seek(self.xref[gen][id], 0)
                    try:
                        pid, pgen = self.readObjectHeader(stream)
                    except ValueError:
                        break
                    if pid == id - self.xrefIndex:
                        self._zeroXref(gen)
                        break
                    #if not, then either it's just plain wrong, or the non-zero-index is actually correct
            stream.seek(loc, 0) #return to where it was

    def _zeroXref(self, generation):
        self.xref[generation] = dict( (k-self.xrefIndex, v) for (k, v) in list(self.xref[generation].items()) )

    def _pairs(self, array):
        i = 0
        while True:
            yield array[i], array[i+1]
            i += 2
            if (i+1) >= len(array):
                break

    def readNextEndLine(self, stream):
        debug = False
        if debug: print(">>readNextEndLine")
        line = b_("")
        while True:
            # Prevent infinite loops in malformed PDFs
            if stream.tell() == 0:
                raise utils.PdfReadError("Could not read malformed PDF file")
            x = stream.read(1)
            if debug: print(("  x:", x, "%x"%ord(x)))
            if stream.tell() < 2:
                raise utils.PdfReadError("EOL marker not found")
            stream.seek(-2, 1)
            if x == b_('\n') or x == b_('\r'): ## \n = LF; \r = CR
                crlf = False
                while x == b_('\n') or x == b_('\r'):
                    if debug:
                        if ord(x) == 0x0D: print("  x is CR 0D")
                        elif ord(x) == 0x0A: print("  x is LF 0A")
                    x = stream.read(1)
                    if x == b_('\n') or x == b_('\r'): # account for CR+LF
                        stream.seek(-1, 1)
                        crlf = True
                    if stream.tell() < 2:
                        raise utils.PdfReadError("EOL marker not found")
                    stream.seek(-2, 1)
                stream.seek(2 if crlf else 1, 1) #if using CR+LF, go back 2 bytes, else 1
                break
            else:
                if debug: print("  x is neither")
                line = x + line
                if debug: print(("  RNEL line:", line))
        if debug: print("leaving RNEL")
        return line

    def decrypt(self, password):
        """
        When using an encrypted / secured PDF file with the PDF Standard
        encryption handler, this function will allow the file to be decrypted.
        It checks the given password against the document's user password and
        owner password, and then stores the resulting decryption key if either
        password is correct.

        It does not matter which password was matched.  Both passwords provide
        the correct decryption key that will allow the document to be used with
        this library.

        :param str password: The password to match.
        :return: ``0`` if the password failed, ``1`` if the password matched the user
            password, and ``2`` if the password matched the owner password.
        :rtype: int
        :raises NotImplementedError: if document uses an unsupported encryption
            method.
        """

        self._override_encryption = True
        try:
            return self._decrypt(password)
        finally:
            self._override_encryption = False

    def _decrypt(self, password):
        encrypt = self.trailer['/Encrypt'].getObject()
        if encrypt['/Filter'] != '/Standard':
            raise NotImplementedError("only Standard PDF encryption handler is available")
        if not (encrypt['/V'] in (1, 2)):
            raise NotImplementedError("only algorithm code 1 and 2 are supported")
        user_password, key = self._authenticateUserPassword(password)
        if user_password:
            self._decryption_key = key
            return 1
        else:
            rev = encrypt['/R'].getObject()
            if rev == 2:
                keylen = 5
            else:
                keylen = encrypt['/Length'].getObject() // 8
            key = _alg33_1(password, rev, keylen)
            real_O = encrypt["/O"].getObject()
            if rev == 2:
                userpass = utils.RC4_encrypt(key, real_O)
            else:
                val = real_O
                for i in range(19, -1, -1):
                    new_key = b_('')
                    for l in range(len(key)):
                        new_key += b_(chr(utils.ord_(key[l]) ^ i))
                    val = utils.RC4_encrypt(new_key, val)
                userpass = val
            owner_password, key = self._authenticateUserPassword(userpass)
            if owner_password:
                self._decryption_key = key
                return 2
        return 0

    def _authenticateUserPassword(self, password):
        encrypt = self.trailer['/Encrypt'].getObject()
        rev = encrypt['/R'].getObject()
        owner_entry = encrypt['/O'].getObject()
        p_entry = encrypt['/P'].getObject()
        id_entry = self.trailer['/ID'].getObject()
        id1_entry = id_entry[0].getObject()
        real_U = encrypt['/U'].getObject().original_bytes
        if rev == 2:
            U, key = _alg34(password, owner_entry, p_entry, id1_entry)
        elif rev >= 3:
            U, key = _alg35(password, rev,
                    encrypt["/Length"].getObject() // 8, owner_entry,
                    p_entry, id1_entry,
                    encrypt.get("/EncryptMetadata", BooleanObject(False)).getObject())
            U, real_U = U[:16], real_U[:16]
        return U == real_U, key

    def getIsEncrypted(self):
        return "/Encrypt" in self.trailer

    isEncrypted = property(lambda self: self.getIsEncrypted(), None, None)
    """
    Read-only boolean property showing whether this PDF file is encrypted.
    Note that this property, if true, will remain true even after the
    :meth:`decrypt()<PdfFileReader.decrypt>` method is called.
    """


def getRectangle(self, name, defaults):
    retval = self.get(name)
    if isinstance(retval, RectangleObject):
        return retval
    if retval == None:
        for d in defaults:
            retval = self.get(d)
            if retval != None:
                break
    if isinstance(retval, IndirectObject):
        retval = self.pdf.getObject(retval)
    retval = RectangleObject(retval)
    setRectangle(self, name, retval)
    return retval


def setRectangle(self, name, value):
    if not isinstance(name, NameObject):
        name = NameObject(name)
    self[name] = value


def deleteRectangle(self, name):
    del self[name]


def createRectangleAccessor(name, fallback):
    return \
        property(
            lambda self: getRectangle(self, name, fallback),
            lambda self, value: setRectangle(self, name, value),
            lambda self: deleteRectangle(self, name)
            )


class PageObject(DictionaryObject):
    """
    This class represents a single page within a PDF file.  Typically this
    object will be created by accessing the
    :meth:`getPage()<PyPDF2.PdfFileReader.getPage>` method of the
    :class:`PdfFileReader<PyPDF2.PdfFileReader>` class, but it is
    also possible to create an empty page with the
    :meth:`createBlankPage()<PageObject.createBlankPage>` static method.

    :param pdf: PDF file the page belongs to.
    :param indirectRef: Stores the original indirect reference to
        this object in its source PDF
    """
    def __init__(self, pdf=None, indirectRef=None):
        DictionaryObject.__init__(self)
        self.pdf = pdf
        self.indirectRef = indirectRef

    def createBlankPage(pdf=None, width=None, height=None):
        """
        Returns a new blank page.
        If ``width`` or ``height`` is ``None``, try to get the page size
        from the last page of *pdf*.

        :param pdf: PDF file the page belongs to
        :param float width: The width of the new page expressed in default user
            space units.
        :param float height: The height of the new page expressed in default user
            space units.
        :return: the new blank page:
        :rtype: :class:`PageObject<PageObject>`
        :raises PageSizeNotDefinedError: if ``pdf`` is ``None`` or contains
            no page
        """
        page = PageObject(pdf)

        # Creates a new page (cf PDF Reference  7.7.3.3)
        page.__setitem__(NameObject('/Type'), NameObject('/Page'))
        page.__setitem__(NameObject('/Parent'), NullObject())
        page.__setitem__(NameObject('/Resources'), DictionaryObject())
        if width is None or height is None:
            if pdf is not None and pdf.getNumPages() > 0:
                lastpage = pdf.getPage(pdf.getNumPages() - 1)
                width = lastpage.mediaBox.getWidth()
                height = lastpage.mediaBox.getHeight()
            else:
                raise utils.PageSizeNotDefinedError()
        page.__setitem__(NameObject('/MediaBox'),
            RectangleObject([0, 0, width, height]))

        return page
    createBlankPage = staticmethod(createBlankPage)

    def rotateClockwise(self, angle):
        """
        Rotates a page clockwise by increments of 90 degrees.

        :param int angle: Angle to rotate the page.  Must be an increment
            of 90 deg.
        """
        assert angle % 90 == 0
        self._rotate(angle)
        return self

    def rotateCounterClockwise(self, angle):
        """
        Rotates a page counter-clockwise by increments of 90 degrees.

        :param int angle: Angle to rotate the page.  Must be an increment
            of 90 deg.
        """
        assert angle % 90 == 0
        self._rotate(-angle)
        return self

    def _rotate(self, angle):
        currentAngle = self.get("/Rotate", 0)
        self[NameObject("/Rotate")] = NumberObject(currentAngle + angle)

    def _mergeResources(res1, res2, resource):
        newRes = DictionaryObject()
        newRes.update(res1.get(resource, DictionaryObject()).getObject())
        page2Res = res2.get(resource, DictionaryObject()).getObject()
        renameRes = {}
        for key in list(page2Res.keys()):
            if key in newRes and newRes.raw_get(key) != page2Res.raw_get(key):
                newname = NameObject(key + str(uuid.uuid4()))
                renameRes[key] = newname
                newRes[newname] = page2Res[key]
            elif key not in newRes:
                newRes[key] = page2Res.raw_get(key)
        return newRes, renameRes
    _mergeResources = staticmethod(_mergeResources)

    def _contentStreamRename(stream, rename, pdf):
        if not rename:
            return stream
        stream = ContentStream(stream, pdf)
        for operands, operator in stream.operations:
            for i in range(len(operands)):
                op = operands[i]
                if isinstance(op, NameObject):
                    operands[i] = rename.get(op,op)
        return stream
    _contentStreamRename = staticmethod(_contentStreamRename)

    def _pushPopGS(contents, pdf):
        # adds a graphics state "push" and "pop" to the beginning and end
        # of a content stream.  This isolates it from changes such as
        # transformation matricies.
        stream = ContentStream(contents, pdf)
        stream.operations.insert(0, [[], "q"])
        stream.operations.append([[], "Q"])
        return stream
    _pushPopGS = staticmethod(_pushPopGS)

    def _addTransformationMatrix(contents, pdf, ctm):
        # adds transformation matrix at the beginning of the given
        # contents stream.
        a, b, c, d, e, f = ctm
        contents = ContentStream(contents, pdf)
        contents.operations.insert(0, [[FloatObject(a), FloatObject(b),
            FloatObject(c), FloatObject(d), FloatObject(e),
            FloatObject(f)], " cm"])
        return contents
    _addTransformationMatrix = staticmethod(_addTransformationMatrix)

    def getContents(self):
        """
        Accesses the page contents.

        :return: the ``/Contents`` object, or ``None`` if it doesn't exist.
            ``/Contents`` is optional, as described in PDF Reference  7.7.3.3
        """
        if "/Contents" in self:
            return self["/Contents"].getObject()
        else:
            return None

    def mergePage(self, page2):
        """
        Merges the content streams of two pages into one.  Resource references
        (i.e. fonts) are maintained from both pages.  The mediabox/cropbox/etc
        of this page are not altered.  The parameter page's content stream will
        be added to the end of this page's content stream, meaning that it will
        be drawn after, or "on top" of this page.

        :param PageObject page2: The page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        """
        self._mergePage(page2)

    def _mergePage(self, page2, page2transformation=None, ctm=None, expand=False):
        # First we work on merging the resource dictionaries.  This allows us
        # to find out what symbols in the content streams we might need to
        # rename.

        newResources = DictionaryObject()
        rename = {}
        originalResources = self["/Resources"].getObject()
        page2Resources = page2["/Resources"].getObject()
        newAnnots = ArrayObject()

        for page in (self, page2):
            if "/Annots" in page:
                annots = page["/Annots"]
                if isinstance(annots, ArrayObject):
                    for ref in annots:
                        newAnnots.append(ref)

        for res in "/ExtGState", "/Font", "/XObject", "/ColorSpace", "/Pattern", "/Shading", "/Properties":
            new, newrename = PageObject._mergeResources(originalResources, page2Resources, res)
            if new:
                newResources[NameObject(res)] = new
                rename.update(newrename)

        # Combine /ProcSet sets.
        newResources[NameObject("/ProcSet")] = ArrayObject(
            frozenset(originalResources.get("/ProcSet", ArrayObject()).getObject()).union(
                frozenset(page2Resources.get("/ProcSet", ArrayObject()).getObject())
            )
        )

        newContentArray = ArrayObject()

        originalContent = self.getContents()
        if originalContent is not None:
            newContentArray.append(PageObject._pushPopGS(
                  originalContent, self.pdf))

        page2Content = page2.getContents()
        if page2Content is not None:
            if page2transformation is not None:
                page2Content = page2transformation(page2Content)
            page2Content = PageObject._contentStreamRename(
                page2Content, rename, self.pdf)
            page2Content = PageObject._pushPopGS(page2Content, self.pdf)
            newContentArray.append(page2Content)

        # if expanding the page to fit a new page, calculate the new media box size
        if expand:
            corners1 = [self.mediaBox.getLowerLeft_x().as_numeric(), self.mediaBox.getLowerLeft_y().as_numeric(),
                        self.mediaBox.getUpperRight_x().as_numeric(), self.mediaBox.getUpperRight_y().as_numeric()]
            corners2 = [page2.mediaBox.getLowerLeft_x().as_numeric(), page2.mediaBox.getLowerLeft_y().as_numeric(),
                        page2.mediaBox.getUpperLeft_x().as_numeric(), page2.mediaBox.getUpperLeft_y().as_numeric(),
                        page2.mediaBox.getUpperRight_x().as_numeric(), page2.mediaBox.getUpperRight_y().as_numeric(),
                        page2.mediaBox.getLowerRight_x().as_numeric(), page2.mediaBox.getLowerRight_y().as_numeric()]
            if ctm is not None:
                ctm = [float(x) for x in ctm]
                new_x = [ctm[0]*corners2[i] + ctm[2]*corners2[i+1] + ctm[4] for i in range(0, 8, 2)]
                new_y = [ctm[1]*corners2[i] + ctm[3]*corners2[i+1] + ctm[5] for i in range(0, 8, 2)]
            else:
                new_x = corners2[0:8:2]
                new_y = corners2[1:8:2]
            lowerleft = [min(new_x), min(new_y)]
            upperright = [max(new_x), max(new_y)]
            lowerleft = [min(corners1[0], lowerleft[0]), min(corners1[1], lowerleft[1])]
            upperright = [max(corners1[2], upperright[0]), max(corners1[3], upperright[1])]

            self.mediaBox.setLowerLeft(lowerleft)
            self.mediaBox.setUpperRight(upperright)

        self[NameObject('/Contents')] = ContentStream(newContentArray, self.pdf)
        self[NameObject('/Resources')] = newResources
        self[NameObject('/Annots')] = newAnnots

    def mergeTransformedPage(self, page2, ctm, expand=False):
        """
        This is similar to mergePage, but a transformation matrix is
        applied to the merged stream.

        :param PageObject page2: The page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param tuple ctm: a 6-element tuple containing the operands of the
            transformation matrix
        :param bool expand: Whether the page should be expanded to fit the dimensions
            of the page to be merged.
        """
        self._mergePage(page2, lambda page2Content:
            PageObject._addTransformationMatrix(page2Content, page2.pdf, ctm), ctm, expand)

    def mergeScaledPage(self, page2, scale, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is scaled
        by appling a transformation matrix.

        :param PageObject page2: The page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float scale: The scaling factor
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """
        # CTM to scale : [ sx 0 0 sy 0 0 ]
        return self.mergeTransformedPage(page2, [scale, 0,
                                                 0,      scale,
                                                 0,      0], expand)

    def mergeRotatedPage(self, page2, rotation, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is rotated
        by appling a transformation matrix.

        :param PageObject page2: the page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float rotation: The angle of the rotation, in degrees
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """
        rotation = math.radians(rotation)
        return self.mergeTransformedPage(page2,
            [math.cos(rotation),  math.sin(rotation),
             -math.sin(rotation), math.cos(rotation),
             0,                   0], expand)

    def mergeTranslatedPage(self, page2, tx, ty, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is translated
        by appling a transformation matrix.

        :param PageObject page2: the page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float tx: The translation on X axis
        :param float ty: The translation on Y axis
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """
        return self.mergeTransformedPage(page2, [1,  0,
                                                 0,  1,
                                                 tx, ty], expand)

    def mergeRotatedTranslatedPage(self, page2, rotation, tx, ty, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is rotated
        and translated by appling a transformation matrix.

        :param PageObject page2: the page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float tx: The translation on X axis
        :param float ty: The translation on Y axis
        :param float rotation: The angle of the rotation, in degrees
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """

        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [-tx, -ty, 1]]
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation), 0],
                    [-math.sin(rotation), math.cos(rotation), 0],
                    [0,                  0,                  1]]
        rtranslation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx, ty, 1]]
        ctm = utils.matrixMultiply(translation, rotating)
        ctm = utils.matrixMultiply(ctm, rtranslation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]], expand)

    def mergeRotatedScaledPage(self, page2, rotation, scale, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is rotated
        and scaled by appling a transformation matrix.

        :param PageObject page2: the page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float rotation: The angle of the rotation, in degrees
        :param float scale: The scaling factor
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation), 0],
                    [-math.sin(rotation), math.cos(rotation), 0],
                    [0,                  0,                  1]]
        scaling = [[scale, 0,    0],
                   [0,    scale, 0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(rotating, scaling)

        return self.mergeTransformedPage(page2,
                                         [ctm[0][0], ctm[0][1],
                                          ctm[1][0], ctm[1][1],
                                          ctm[2][0], ctm[2][1]], expand)

    def mergeScaledTranslatedPage(self, page2, scale, tx, ty, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is translated
        and scaled by appling a transformation matrix.

        :param PageObject page2: the page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float scale: The scaling factor
        :param float tx: The translation on X axis
        :param float ty: The translation on Y axis
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """

        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx, ty, 1]]
        scaling = [[scale, 0,    0],
                   [0,    scale, 0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(scaling, translation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]], expand)

    def mergeRotatedScaledTranslatedPage(self, page2, rotation, scale, tx, ty, expand=False):
        """
        This is similar to mergePage, but the stream to be merged is translated,
        rotated and scaled by appling a transformation matrix.

        :param PageObject page2: the page to be merged into this one. Should be
            an instance of :class:`PageObject<PageObject>`.
        :param float tx: The translation on X axis
        :param float ty: The translation on Y axis
        :param float rotation: The angle of the rotation, in degrees
        :param float scale: The scaling factor
        :param bool expand: Whether the page should be expanded to fit the
            dimensions of the page to be merged.
        """
        translation = [[1, 0, 0],
                       [0, 1, 0],
                       [tx, ty, 1]]
        rotation = math.radians(rotation)
        rotating = [[math.cos(rotation), math.sin(rotation), 0],
                    [-math.sin(rotation), math.cos(rotation), 0],
                    [0,                  0,                  1]]
        scaling = [[scale, 0,    0],
                   [0,    scale, 0],
                   [0,    0,    1]]
        ctm = utils.matrixMultiply(rotating, scaling)
        ctm = utils.matrixMultiply(ctm, translation)

        return self.mergeTransformedPage(page2, [ctm[0][0], ctm[0][1],
                                                 ctm[1][0], ctm[1][1],
                                                 ctm[2][0], ctm[2][1]], expand)

    ##
    # Applys a transformation matrix the page.
    #
    # @param ctm   A 6 elements tuple containing the operands of the
    #              transformation matrix
    def addTransformation(self, ctm):
        """
        Applies a transformation matrix to the page.

        :param tuple ctm: A 6-element tuple containing the operands of the
            transformation matrix.
        """
        originalContent = self.getContents()
        if originalContent is not None:
            newContent = PageObject._addTransformationMatrix(
                originalContent, self.pdf, ctm)
            newContent = PageObject._pushPopGS(newContent, self.pdf)
            self[NameObject('/Contents')] = newContent

    def scale(self, sx, sy):
        """
        Scales a page by the given factors by appling a transformation
        matrix to its content and updating the page size.

        :param float sx: The scaling factor on horizontal axis.
        :param float sy: The scaling factor on vertical axis.
        """
        self.addTransformation([sx, 0,
                                0,  sy,
                                0,  0])
        self.mediaBox = RectangleObject([
            float(self.mediaBox.getLowerLeft_x()) * sx,
            float(self.mediaBox.getLowerLeft_y()) * sy,
            float(self.mediaBox.getUpperRight_x()) * sx,
            float(self.mediaBox.getUpperRight_y()) * sy])
        if "/VP" in self:
            viewport = self["/VP"]
            if isinstance(viewport, ArrayObject):
                bbox = viewport[0]["/BBox"]
            else:
                bbox = viewport["/BBox"]
            scaled_bbox = RectangleObject([
                float(bbox[0]) * sx,
                float(bbox[1]) * sy,
                float(bbox[2]) * sx,
                float(bbox[3]) * sy])
            if isinstance(viewport, ArrayObject):
                self[NameObject("/VP")][NumberObject(0)][NameObject("/BBox")] = scaled_bbox
            else:
                self[NameObject("/VP")][NameObject("/BBox")] = scaled_bbox

    def scaleBy(self, factor):
        """
        Scales a page by the given factor by appling a transformation
        matrix to its content and updating the page size.

        :param float factor: The scaling factor (for both X and Y axis).
        """
        self.scale(factor, factor)

    def scaleTo(self, width, height):
        """
        Scales a page to the specified dimentions by appling a
        transformation matrix to its content and updating the page size.

        :param float width: The new width.
        :param float height: The new heigth.
        """
        sx = width / float(self.mediaBox.getUpperRight_x() -
                      self.mediaBox.getLowerLeft_x ())
        sy = height / float(self.mediaBox.getUpperRight_y() -
                       self.mediaBox.getLowerLeft_y ())
        self.scale(sx, sy)

    def compressContentStreams(self):
        """
        Compresses the size of this page by joining all content streams and
        applying a FlateDecode filter.

        However, it is possible that this function will perform no action if
        content stream compression becomes "automatic" for some reason.
        """
        content = self.getContents()
        if content is not None:
            if not isinstance(content, ContentStream):
                content = ContentStream(content, self.pdf)
            self[NameObject("/Contents")] = content.flateEncode()

    def extractText(self):
        """
        Locate all text drawing commands, in the order they are provided in the
        content stream, and extract the text.  This works well for some PDF
        files, but poorly for others, depending on the generator used.  This will
        be refined in the future.  Do not rely on the order of text coming out of
        this function, as it will change if this function is made more
        sophisticated.

        :return: a unicode string object.
        """
        text = u_("")
        content = self["/Contents"].getObject()
        if not isinstance(content, ContentStream):
            content = ContentStream(content, self.pdf)
        # Note: we check all strings are TextStringObjects.  ByteStringObjects
        # are strings where the byte->string encoding was unknown, so adding
        # them to the text here would be gibberish.
        for operands, operator in content.operations:
            if operator == b_("Tj"):
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += _text
            elif operator == b_("T*"):
                text += "\n"
            elif operator == b_("'"):
                text += "\n"
                _text = operands[0]
                if isinstance(_text, TextStringObject):
                    text += operands[0]
            elif operator == b_('"'):
                _text = operands[2]
                if isinstance(_text, TextStringObject):
                    text += "\n"
                    text += _text
            elif operator == b_("TJ"):
                for i in operands[0]:
                    if isinstance(i, TextStringObject):
                        text += i
                text += "\n"
        return text

    mediaBox = createRectangleAccessor("/MediaBox", ())
    """
    A :class:`RectangleObject<PyPDF2.generic.RectangleObject>`, expressed in default user space units,
    defining the boundaries of the physical medium on which the page is
    intended to be displayed or printed.
    """

    cropBox = createRectangleAccessor("/CropBox", ("/MediaBox",))
    """
    A :class:`RectangleObject<PyPDF2.generic.RectangleObject>`, expressed in default user space units,
    defining the visible region of default user space.  When the page is
    displayed or printed, its contents are to be clipped (cropped) to this
    rectangle and then imposed on the output medium in some
    implementation-defined manner.  Default value: same as :attr:`mediaBox<mediaBox>`.
    """

    bleedBox = createRectangleAccessor("/BleedBox", ("/CropBox", "/MediaBox"))
    """
    A :class:`RectangleObject<PyPDF2.generic.RectangleObject>`, expressed in default user space units,
    defining the region to which the contents of the page should be clipped
    when output in a production enviroment.
    """

    trimBox = createRectangleAccessor("/TrimBox", ("/CropBox", "/MediaBox"))
    """
    A :class:`RectangleObject<PyPDF2.generic.RectangleObject>`, expressed in default user space units,
    defining the intended dimensions of the finished page after trimming.
    """

    artBox = createRectangleAccessor("/ArtBox", ("/CropBox", "/MediaBox"))
    """
    A :class:`RectangleObject<PyPDF2.generic.RectangleObject>`, expressed in default user space units,
    defining the extent of the page's meaningful content as intended by the
    page's creator.
    """


class ContentStream(DecodedStreamObject):
    def __init__(self, stream, pdf):
        self.pdf = pdf
        self.operations = []
        # stream may be a StreamObject or an ArrayObject containing
        # multiple StreamObjects to be cat'd together.
        stream = stream.getObject()
        if isinstance(stream, ArrayObject):
            data = b_("")
            for s in stream:
                data += s.getObject().getData()
            stream = BytesIO(b_(data))
        else:
            stream = BytesIO(b_(stream.getData()))
        self.__parseContentStream(stream)

    def __parseContentStream(self, stream):
        # file("f:\\tmp.txt", "w").write(stream.read())
        stream.seek(0, 0)
        operands = []
        while True:
            peek = readNonWhitespace(stream)
            if peek == b_('') or ord_(peek) == 0:
                break
            stream.seek(-1, 1)
            if peek.isalpha() or peek == b_("'") or peek == b_('"'):
                operator = utils.readUntilRegex(stream,
                        NameObject.delimiterPattern, True)
                if operator == b_("BI"):
                    # begin inline image - a completely different parsing
                    # mechanism is required, of course... thanks buddy...
                    assert operands == []
                    ii = self._readInlineImage(stream)
                    self.operations.append((ii, b_("INLINE IMAGE")))
                else:
                    self.operations.append((operands, operator))
                    operands = []
            elif peek == b_('%'):
                # If we encounter a comment in the content stream, we have to
                # handle it here.  Typically, readObject will handle
                # encountering a comment -- but readObject assumes that
                # following the comment must be the object we're trying to
                # read.  In this case, it could be an operator instead.
                while peek not in (b_('\r'), b_('\n')):
                    peek = stream.read(1)
            else:
                operands.append(readObject(stream, None))

    def _readInlineImage(self, stream):
        # begin reading just after the "BI" - begin image
        # first read the dictionary of settings.
        settings = DictionaryObject()
        while True:
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            if tok == b_("I"):
                # "ID" - begin of image data
                break
            key = readObject(stream, self.pdf)
            tok = readNonWhitespace(stream)
            stream.seek(-1, 1)
            value = readObject(stream, self.pdf)
            settings[key] = value
        # left at beginning of ID
        tmp = stream.read(3)
        assert tmp[:2] == b_("ID")
        data = b_("")
        while True:
            # Read the inline image, while checking for EI (End Image) operator.
            tok = stream.read(1)
            if tok == b_("E"):
                # Check for End Image
                tok2 = stream.read(1)
                if tok2 == b_("I"):
                    # Data can contain EI, so check for the Q operator.
                    tok3 = stream.read(1)
                    info = tok + tok2
                    # We need to find whitespace between EI and Q.
                    has_q_whitespace = False
                    while tok3 in utils.WHITESPACES:
                        has_q_whitespace = True
                        info += tok3
                        tok3 = stream.read(1)
                    if tok3 == b_("Q") and has_q_whitespace:
                        stream.seek(-1, 1)
                        break
                    else:
                        stream.seek(-1,1)
                        data += info
                else:
                    stream.seek(-1, 1)
                    data += tok
            else:
                data += tok
        return {"settings": settings, "data": data}

    def _getData(self):
        newdata = BytesIO()
        for operands, operator in self.operations:
            if operator == b_("INLINE IMAGE"):
                newdata.write(b_("BI"))
                dicttext = BytesIO()
                operands["settings"].writeToStream(dicttext, None)
                newdata.write(dicttext.getvalue()[2:-2])
                newdata.write(b_("ID "))
                newdata.write(operands["data"])
                newdata.write(b_("EI"))
            else:
                for op in operands:
                    op.writeToStream(newdata, None)
                    newdata.write(b_(" "))
                newdata.write(b_(operator))
            newdata.write(b_("\n"))
        return newdata.getvalue()

    def _setData(self, value):
        self.__parseContentStream(BytesIO(b_(value)))

    _data = property(_getData, _setData)


class DocumentInformation(DictionaryObject):
    """
    A class representing the basic document metadata provided in a PDF File.
    This class is accessible through
    :meth:`getDocumentInfo()<PyPDF2.PdfFileReader.getDocumentInfo()>`

    All text properties of the document metadata have
    *two* properties, eg. author and author_raw. The non-raw property will
    always return a ``TextStringObject``, making it ideal for a case where
    the metadata is being displayed. The raw property can sometimes return
    a ``ByteStringObject``, if PyPDF2 was unable to decode the string's
    text encoding; this requires additional safety in the caller and
    therefore is not as commonly accessed.
    """

    def __init__(self):
        DictionaryObject.__init__(self)

    def getText(self, key):
        retval = self.get(key, None)
        if isinstance(retval, TextStringObject):
            return retval
        return None

    title = property(lambda self: self.getText("/Title"))
    """Read-only property accessing the document's **title**.
    Returns a unicode string (``TextStringObject``) or ``None``
    if the title is not specified."""
    title_raw = property(lambda self: self.get("/Title"))
    """The "raw" version of title; can return a ``ByteStringObject``."""

    author = property(lambda self: self.getText("/Author"))
    """Read-only property accessing the document's **author**.
    Returns a unicode string (``TextStringObject``) or ``None``
    if the author is not specified."""
    author_raw = property(lambda self: self.get("/Author"))
    """The "raw" version of author; can return a ``ByteStringObject``."""

    subject = property(lambda self: self.getText("/Subject"))
    """Read-only property accessing the document's **subject**.
    Returns a unicode string (``TextStringObject``) or ``None``
    if the subject is not specified."""
    subject_raw = property(lambda self: self.get("/Subject"))
    """The "raw" version of subject; can return a ``ByteStringObject``."""

    creator = property(lambda self: self.getText("/Creator"))
    """Read-only property accessing the document's **creator**. If the
    document was converted to PDF from another format, this is the name of the
    application (e.g. OpenOffice) that created the original document from
    which it was converted. Returns a unicode string (``TextStringObject``)
    or ``None`` if the creator is not specified."""
    creator_raw = property(lambda self: self.get("/Creator"))
    """The "raw" version of creator; can return a ``ByteStringObject``."""

    producer = property(lambda self: self.getText("/Producer"))
    """Read-only property accessing the document's **producer**.
    If the document was converted to PDF from another format, this is
    the name of the application (for example, OSX Quartz) that converted
    it to PDF. Returns a unicode string (``TextStringObject``)
    or ``None`` if the producer is not specified."""
    producer_raw = property(lambda self: self.get("/Producer"))
    """The "raw" version of producer; can return a ``ByteStringObject``."""


def convertToInt(d, size):
    if size > 8:
        raise utils.PdfReadError("invalid size in convertToInt")
    d = b_("\x00\x00\x00\x00\x00\x00\x00\x00") + b_(d)
    d = d[-8:]
    return struct.unpack(">q", d)[0]

# ref: pdf1.8 spec section 3.5.2 algorithm 3.2
_encryption_padding = b_('\x28\xbf\x4e\x5e\x4e\x75\x8a\x41\x64\x00\x4e\x56') + \
        b_('\xff\xfa\x01\x08\x2e\x2e\x00\xb6\xd0\x68\x3e\x80\x2f\x0c') + \
        b_('\xa9\xfe\x64\x53\x69\x7a')


# Implementation of algorithm 3.2 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt=True):
    # 1. Pad or truncate the password string to exactly 32 bytes.  If the
    # password string is more than 32 bytes long, use only its first 32 bytes;
    # if it is less than 32 bytes long, pad it by appending the required number
    # of additional bytes from the beginning of the padding string
    # (_encryption_padding).
    password = b_((str_(password) + str_(_encryption_padding))[:32])
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    import struct
    m = md5(password)
    # 3. Pass the value of the encryption dictionary's /O entry to the MD5 hash
    # function.
    m.update(owner_entry.original_bytes)
    # 4. Treat the value of the /P entry as an unsigned 4-byte integer and pass
    # these bytes to the MD5 hash function, low-order byte first.
    p_entry = struct.pack('<i', p_entry)
    m.update(p_entry)
    # 5. Pass the first element of the file's file identifier array to the MD5
    # hash function.
    m.update(id1_entry.original_bytes)
    # 6. (Revision 3 or greater) If document metadata is not being encrypted,
    # pass 4 bytes with the value 0xFFFFFFFF to the MD5 hash function.
    if rev >= 3 and not metadata_encrypt:
        m.update(b_("\xff\xff\xff\xff"))
    # 7. Finish the hash.
    md5_hash = m.digest()
    # 8. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass the first n bytes of the output as
    # input into a new MD5 hash, where n is the number of bytes of the
    # encryption key as defined by the value of the encryption dictionary's
    # /Length entry.
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash[:keylen]).digest()
    # 9. Set the encryption key to the first n bytes of the output from the
    # final MD5 hash, where n is always 5 for revision 2 but, for revision 3 or
    # greater, depends on the value of the encryption dictionary's /Length
    # entry.
    return md5_hash[:keylen]


# Implementation of algorithm 3.3 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg33(owner_pwd, user_pwd, rev, keylen):
    # steps 1 - 4
    key = _alg33_1(owner_pwd, rev, keylen)
    # 5. Pad or truncate the user password string as described in step 1 of
    # algorithm 3.2.
    user_pwd = b_((user_pwd + str_(_encryption_padding))[:32])
    # 6. Encrypt the result of step 5, using an RC4 encryption function with
    # the encryption key obtained in step 4.
    val = utils.RC4_encrypt(key, user_pwd)
    # 7. (Revision 3 or greater) Do the following 19 times: Take the output
    # from the previous invocation of the RC4 function and pass it as input to
    # a new invocation of the function; use an encryption key generated by
    # taking each byte of the encryption key obtained in step 4 and performing
    # an XOR operation between that byte and the single-byte value of the
    # iteration counter (from 1 to 19).
    if rev >= 3:
        for i in range(1, 20):
            new_key = ''
            for l in range(len(key)):
                new_key += chr(ord_(key[l]) ^ i)
            val = utils.RC4_encrypt(new_key, val)
    # 8. Store the output from the final invocation of the RC4 as the value of
    # the /O entry in the encryption dictionary.
    return val


# Steps 1-4 of algorithm 3.3
def _alg33_1(password, rev, keylen):
    # 1. Pad or truncate the owner password string as described in step 1 of
    # algorithm 3.2.  If there is no owner password, use the user password
    # instead.
    password = b_((password + str_(_encryption_padding))[:32])
    # 2. Initialize the MD5 hash function and pass the result of step 1 as
    # input to this function.
    m = md5(password)
    # 3. (Revision 3 or greater) Do the following 50 times: Take the output
    # from the previous MD5 hash and pass it as input into a new MD5 hash.
    md5_hash = m.digest()
    if rev >= 3:
        for i in range(50):
            md5_hash = md5(md5_hash).digest()
    # 4. Create an RC4 encryption key using the first n bytes of the output
    # from the final MD5 hash, where n is always 5 for revision 2 but, for
    # revision 3 or greater, depends on the value of the encryption
    # dictionary's /Length entry.
    key = md5_hash[:keylen]
    return key


# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg34(password, owner_entry, p_entry, id1_entry):
    # 1. Create an encryption key based on the user password string, as
    # described in algorithm 3.2.
    key = _alg32(password, 2, 5, owner_entry, p_entry, id1_entry)
    # 2. Encrypt the 32-byte padding string shown in step 1 of algorithm 3.2,
    # using an RC4 encryption function with the encryption key from the
    # preceding step.
    U = utils.RC4_encrypt(key, _encryption_padding)
    # 3. Store the result of step 2 as the value of the /U entry in the
    # encryption dictionary.
    return U, key


# Implementation of algorithm 3.4 of the PDF standard security handler,
# section 3.5.2 of the PDF 1.6 reference.
def _alg35(password, rev, keylen, owner_entry, p_entry, id1_entry, metadata_encrypt):
    # 1. Create an encryption key based on the user password string, as
    # described in Algorithm 3.2.
    key = _alg32(password, rev, keylen, owner_entry, p_entry, id1_entry)
    # 2. Initialize the MD5 hash function and pass the 32-byte padding string
    # shown in step 1 of Algorithm 3.2 as input to this function.
    m = md5()
    m.update(_encryption_padding)
    # 3. Pass the first element of the file's file identifier array (the value
    # of the ID entry in the document's trailer dictionary; see Table 3.13 on
    # page 73) to the hash function and finish the hash.  (See implementation
    # note 25 in Appendix H.)
    m.update(id1_entry.original_bytes)
    md5_hash = m.digest()
    # 4. Encrypt the 16-byte result of the hash, using an RC4 encryption
    # function with the encryption key from step 1.
    val = utils.RC4_encrypt(key, md5_hash)
    # 5. Do the following 19 times: Take the output from the previous
    # invocation of the RC4 function and pass it as input to a new invocation
    # of the function; use an encryption key generated by taking each byte of
    # the original encryption key (obtained in step 2) and performing an XOR
    # operation between that byte and the single-byte value of the iteration
    # counter (from 1 to 19).
    for i in range(1, 20):
        new_key = b_('')
        for l in range(len(key)):
            new_key += b_(chr(ord_(key[l]) ^ i))
        val = utils.RC4_encrypt(new_key, val)
    # 6. Append 16 bytes of arbitrary padding to the output from the final
    # invocation of the RC4 function and store the 32-byte result as the value
    # of the U entry in the encryption dictionary.
    # (implementator note: I don't know what "arbitrary padding" is supposed to
    # mean, so I have used null bytes.  This seems to match a few other
    # people's implementations)
    return val + (b_('\x00') * 16), key
