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

import codecs
import collections
import decimal
import logging
import random
import struct
import time
import uuid
import warnings
from hashlib import md5
from io import BufferedReader, BufferedWriter, BytesIO, FileIO
from pathlib import Path
from types import TracebackType
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from ._page import PageObject, _VirtualList
from ._reader import PdfReader
from ._security import _alg33, _alg34, _alg35
from ._utils import (
    StrByteType,
    StreamType,
    _get_max_pdf_version_header,
    b_,
    deprecate_bookmark,
    deprecate_with_replacement,
    logger_warning,
)
from .constants import AnnotationDictionaryAttributes
from .constants import CatalogAttributes as CA
from .constants import CatalogDictionary
from .constants import Core as CO
from .constants import EncryptionDictAttributes as ED
from .constants import (
    FieldDictionaryAttributes,
    FieldFlag,
    FileSpecificationDictionaryEntries,
    GoToActionArguments,
    InteractiveFormDictEntries,
)
from .constants import PageAttributes as PG
from .constants import PagesAttributes as PA
from .constants import StreamAttributes as SA
from .constants import TrailerKeys as TK
from .constants import TypFitArguments, UserAccessPermissions
from .generic import (
    AnnotationBuilder,
    ArrayObject,
    BooleanObject,
    ByteStringObject,
    ContentStream,
    DecodedStreamObject,
    Destination,
    DictionaryObject,
    FloatObject,
    IndirectObject,
    NameObject,
    NullObject,
    NumberObject,
    PdfObject,
    RectangleObject,
    StreamObject,
    TextStringObject,
    TreeObject,
    create_string_object,
    hex_to_rgb,
)
from .types import (
    BorderArrayType,
    FitType,
    LayoutType,
    OutlineItemType,
    PagemodeType,
    ZoomArgsType,
    ZoomArgType,
)

logger = logging.getLogger(__name__)


OPTIONAL_READ_WRITE_FIELD = FieldFlag(0)
ALL_DOCUMENT_PERMISSIONS = UserAccessPermissions((2**31 - 1) - 3)


class PdfWriter:
    """
    This class supports writing PDF files out, given pages produced by another
    class (typically :class:`PdfReader<PyPDF2.PdfReader>`).
    """

    def __init__(self, fileobj: StrByteType = "") -> None:
        self._header = b"%PDF-1.3"
        self._objects: List[PdfObject] = []  # array of indirect objects
        self._idnum_hash: Dict[bytes, IndirectObject] = {}

        # The root of our page tree node.
        pages = DictionaryObject()
        pages.update(
            {
                NameObject(PA.TYPE): NameObject("/Pages"),
                NameObject(PA.COUNT): NumberObject(0),
                NameObject(PA.KIDS): ArrayObject(),
            }
        )
        self._pages = self._add_object(pages)

        # info object
        info = DictionaryObject()
        info.update(
            {
                NameObject("/Producer"): create_string_object(
                    codecs.BOM_UTF16_BE + "PyPDF2".encode("utf-16be")
                )
            }
        )
        self._info = self._add_object(info)

        # root object
        root = DictionaryObject()
        root.update(
            {
                NameObject(PA.TYPE): NameObject(CO.CATALOG),
                NameObject(CO.PAGES): self._pages,
            }
        )
        self._root: Optional[IndirectObject] = None
        self._root_object = root
        self.fileobj = fileobj
        self.with_as_usage = False

    def __enter__(self) -> "PdfWriter":
        """Store that writer is initialized by 'with'."""
        self.with_as_usage = True
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        """Write data to the fileobj."""
        if self.fileobj:
            self.write(self.fileobj)

    @property
    def pdf_header(self) -> bytes:
        """
        Header of the PDF document that is written.

        This should be something like b'%PDF-1.5'. It is recommended to set the
        lowest version that supports all features which are used within the
        PDF file.
        """
        return self._header

    @pdf_header.setter
    def pdf_header(self, new_header: bytes) -> None:
        self._header = new_header

    def _add_object(self, obj: PdfObject) -> IndirectObject:
        self._objects.append(obj)
        return IndirectObject(len(self._objects), 0, self)

    def get_object(
        self,
        indirect_reference: Optional[IndirectObject] = None,
        ido: Optional[IndirectObject] = None,
    ) -> PdfObject:
        if ido is not None:  # deprecated
            if indirect_reference is not None:
                raise ValueError(
                    "Please only set 'indirect_reference'. The 'ido' argument is deprecated."
                )
            else:
                indirect_reference = ido
                warnings.warn(
                    "The parameter 'ido' is depreciated and will be removed in PyPDF2 3.0.0.",
                    DeprecationWarning,
                )
        assert (
            indirect_reference is not None
        )  # the None value is only there to keep the deprecated name
        if indirect_reference.pdf != self:
            raise ValueError("pdf must be self")
        return self._objects[indirect_reference.idnum - 1]  # type: ignore

    def getObject(self, ido: IndirectObject) -> PdfObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`get_object` instead.
        """
        deprecate_with_replacement("getObject", "get_object")
        return self.get_object(ido)

    def _add_page(
        self, page: PageObject, action: Callable[[Any, IndirectObject], None]
    ) -> None:
        assert cast(str, page[PA.TYPE]) == CO.PAGE
        if page.pdf is not None:
            other = page.pdf.pdf_header
            if isinstance(other, str):
                other = other.encode()  # type: ignore
            self.pdf_header = _get_max_pdf_version_header(self.pdf_header, other)  # type: ignore
        page[NameObject(PA.PARENT)] = self._pages
        page_ind = self._add_object(page)
        pages = cast(DictionaryObject, self.get_object(self._pages))
        action(pages[PA.KIDS], page_ind)
        page_count = cast(int, pages[PA.COUNT])
        pages[NameObject(PA.COUNT)] = NumberObject(page_count + 1)

    def set_need_appearances_writer(self) -> None:
        # See 12.7.2 and 7.7.2 for more information:
        # http://www.adobe.com/content/dam/acom/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
        try:
            catalog = self._root_object
            # get the AcroForm tree
            if CatalogDictionary.ACRO_FORM not in catalog:
                self._root_object.update(
                    {
                        NameObject(CatalogDictionary.ACRO_FORM): IndirectObject(
                            len(self._objects), 0, self
                        )
                    }
                )

            need_appearances = NameObject(InteractiveFormDictEntries.NeedAppearances)
            self._root_object[CatalogDictionary.ACRO_FORM][need_appearances] = BooleanObject(True)  # type: ignore
        except Exception as exc:
            logger.error("set_need_appearances_writer() catch : ", repr(exc))

    def add_page(self, page: PageObject) -> None:
        """
        Add a page to this PDF file.

        The page is usually acquired from a :class:`PdfReader<PyPDF2.PdfReader>`
        instance.

        :param PageObject page: The page to add to the document. Should be
            an instance of :class:`PageObject<PyPDF2._page.PageObject>`
        """
        self._add_page(page, list.append)

    def addPage(self, page: PageObject) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_page` instead.
        """
        deprecate_with_replacement("addPage", "add_page")
        self.add_page(page)

    def insert_page(self, page: PageObject, index: int = 0) -> None:
        """
        Insert a page in this PDF file. The page is usually acquired from a
        :class:`PdfReader<PyPDF2.PdfReader>` instance.

        :param PageObject page: The page to add to the document.
        :param int index: Position at which the page will be inserted.
        """
        self._add_page(page, lambda l, p: l.insert(index, p))

    def insertPage(self, page: PageObject, index: int = 0) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`insert_page` instead.
        """
        deprecate_with_replacement("insertPage", "insert_page")
        self.insert_page(page, index)

    def get_page(
        self, page_number: Optional[int] = None, pageNumber: Optional[int] = None
    ) -> PageObject:
        """
        Retrieve a page by number from this PDF file.

        :param int page_number: The page number to retrieve
            (pages begin at zero)
        :return: the page at the index given by *page_number*
        """
        if pageNumber is not None:  # pragma: no cover
            if page_number is not None:
                raise ValueError("Please only use the page_number parameter")
            deprecate_with_replacement(
                "get_page(pageNumber)", "get_page(page_number)", "4.0.0"
            )
            page_number = pageNumber
        if page_number is None and pageNumber is None:  # pragma: no cover
            raise ValueError("Please specify the page_number")
        pages = cast(Dict[str, Any], self.get_object(self._pages))
        # TODO: crude hack
        return cast(PageObject, pages[PA.KIDS][page_number].get_object())

    def getPage(self, pageNumber: int) -> PageObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :code:`writer.pages[page_number]` instead.
        """
        deprecate_with_replacement("getPage", "writer.pages[page_number]")
        return self.get_page(pageNumber)

    def _get_num_pages(self) -> int:
        pages = cast(Dict[str, Any], self.get_object(self._pages))
        return int(pages[NameObject("/Count")])

    def getNumPages(self) -> int:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :code:`len(writer.pages)` instead.
        """
        deprecate_with_replacement("getNumPages", "len(writer.pages)")
        return self._get_num_pages()

    @property
    def pages(self) -> List[PageObject]:
        """Property that emulates a list of :class:`PageObject<PyPDF2._page.PageObject>`."""
        return _VirtualList(self._get_num_pages, self.get_page)  # type: ignore

    def add_blank_page(
        self, width: Optional[float] = None, height: Optional[float] = None
    ) -> PageObject:
        """
        Append a blank page to this PDF file and returns it. If no page size
        is specified, use the size of the last page.

        :param float width: The width of the new page expressed in default user
            space units.
        :param float height: The height of the new page expressed in default
            user space units.
        :return: the newly appended page
        :raises PageSizeNotDefinedError: if width and height are not defined
            and previous page does not exist.
        """
        page = PageObject.create_blank_page(self, width, height)
        self.add_page(page)
        return page

    def addBlankPage(
        self, width: Optional[float] = None, height: Optional[float] = None
    ) -> PageObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_blank_page` instead.
        """
        deprecate_with_replacement("addBlankPage", "add_blank_page")
        return self.add_blank_page(width, height)

    def insert_blank_page(
        self,
        width: Optional[decimal.Decimal] = None,
        height: Optional[decimal.Decimal] = None,
        index: int = 0,
    ) -> PageObject:
        """
        Insert a blank page to this PDF file and returns it. If no page size
        is specified, use the size of the last page.

        :param float width: The width of the new page expressed in default user
            space units.
        :param float height: The height of the new page expressed in default
            user space units.
        :param int index: Position to add the page.
        :return: the newly appended page
        :raises PageSizeNotDefinedError: if width and height are not defined
            and previous page does not exist.
        """
        if width is None or height is None and (self._get_num_pages() - 1) >= index:
            oldpage = self.pages[index]
            width = oldpage.mediabox.width
            height = oldpage.mediabox.height
        page = PageObject.create_blank_page(self, width, height)
        self.insert_page(page, index)
        return page

    def insertBlankPage(
        self,
        width: Optional[decimal.Decimal] = None,
        height: Optional[decimal.Decimal] = None,
        index: int = 0,
    ) -> PageObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`insertBlankPage` instead.
        """
        deprecate_with_replacement("insertBlankPage", "insert_blank_page")
        return self.insert_blank_page(width, height, index)

    @property
    def open_destination(
        self,
    ) -> Union[None, Destination, TextStringObject, ByteStringObject]:
        """
        Property to access the opening destination ("/OpenAction" entry in the
        PDF catalog).
        it returns `None` if the entry does not exist is not set.

        :param destination:.
        the property can be set to a Destination, a Page or an string(NamedDest) or
            None (to remove "/OpenAction")

        (value stored in "/OpenAction" entry in the Pdf Catalog)
        """
        if "/OpenAction" not in self._root_object:
            return None
        oa = self._root_object["/OpenAction"]
        if isinstance(oa, (str, bytes)):
            return create_string_object(str(oa))
        elif isinstance(oa, ArrayObject):
            try:
                page, typ = oa[0:2]  # type: ignore
                array = oa[2:]
                return Destination("OpenAction", page, typ, *array)  # type: ignore
            except Exception:
                raise Exception(f"Invalid Destination {oa}")
        else:
            return None

    @open_destination.setter
    def open_destination(self, dest: Union[None, str, Destination, PageObject]) -> None:
        if dest is None:
            try:
                del self._root_object["/OpenAction"]
            except KeyError:
                pass
        elif isinstance(dest, str):
            self._root_object[NameObject("/OpenAction")] = TextStringObject(dest)
        elif isinstance(dest, Destination):
            self._root_object[NameObject("/OpenAction")] = dest.dest_array
        elif isinstance(dest, PageObject):
            self._root_object[NameObject("/OpenAction")] = Destination(
                "Opening",
                dest.indirect_reference
                if dest.indirect_reference is not None
                else NullObject(),
                TextStringObject("/Fit"),
            ).dest_array

    def add_js(self, javascript: str) -> None:
        """
        Add Javascript which will launch upon opening this PDF.

        :param str javascript: Your Javascript.

        >>> output.add_js("this.print({bUI:true,bSilent:false,bShrinkToFit:true});")
        # Example: This will launch the print window when the PDF is opened.
        """
        # Names / JavaScript prefered to be able to add multiple scripts
        if "/Names" not in self._root_object:
            self._root_object[NameObject(CA.NAMES)] = DictionaryObject()
        names = cast(DictionaryObject, self._root_object[CA.NAMES])
        if "/JavaScript" not in names:
            names[NameObject("/JavaScript")] = DictionaryObject(
                {NameObject("/Names"): ArrayObject()}
            )
            # cast(DictionaryObject, names[NameObject("/JavaScript")])[NameObject("/Names")] = ArrayObject()
        js_list = cast(
            ArrayObject, cast(DictionaryObject, names["/JavaScript"])["/Names"]
        )

        js = DictionaryObject()
        js.update(
            {
                NameObject(PA.TYPE): NameObject("/Action"),
                NameObject("/S"): NameObject("/JavaScript"),
                NameObject("/JS"): TextStringObject(f"{javascript}"),
            }
        )
        # We need a name for parameterized javascript in the pdf file, but it can be anything.
        js_list.append(create_string_object(str(uuid.uuid4())))
        js_list.append(self._add_object(js))

    def addJS(self, javascript: str) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_js` instead.
        """
        deprecate_with_replacement("addJS", "add_js")
        return self.add_js(javascript)

    def add_attachment(self, filename: str, data: Union[str, bytes]) -> None:
        """
        Embed a file inside the PDF.

        :param str filename: The filename to display.
        :param str data: The data in the file.

        Reference:
        https://www.adobe.com/content/dam/Adobe/en/devnet/acrobat/pdfs/PDF32000_2008.pdf
        Section 7.11.3
        """
        # We need three entries:
        # * The file's data
        # * The /Filespec entry
        # * The file's name, which goes in the Catalog

        # The entry for the file
        # Sample:
        # 8 0 obj
        # <<
        #  /Length 12
        #  /Type /EmbeddedFile
        # >>
        # stream
        # Hello world!
        # endstream
        # endobj

        file_entry = DecodedStreamObject()
        file_entry.set_data(data)
        file_entry.update({NameObject(PA.TYPE): NameObject("/EmbeddedFile")})

        # The Filespec entry
        # Sample:
        # 7 0 obj
        # <<
        #  /Type /Filespec
        #  /F (hello.txt)
        #  /EF << /F 8 0 R >>
        # >>

        ef_entry = DictionaryObject()
        ef_entry.update({NameObject("/F"): file_entry})

        filespec = DictionaryObject()
        filespec.update(
            {
                NameObject(PA.TYPE): NameObject("/Filespec"),
                NameObject(FileSpecificationDictionaryEntries.F): create_string_object(
                    filename
                ),  # Perhaps also try TextStringObject
                NameObject(FileSpecificationDictionaryEntries.EF): ef_entry,
            }
        )

        # Then create the entry for the root, as it needs a reference to the Filespec
        # Sample:
        # 1 0 obj
        # <<
        #  /Type /Catalog
        #  /Outlines 2 0 R
        #  /Pages 3 0 R
        #  /Names << /EmbeddedFiles << /Names [(hello.txt) 7 0 R] >> >>
        # >>
        # endobj

        embedded_files_names_dictionary = DictionaryObject()
        embedded_files_names_dictionary.update(
            {
                NameObject(CA.NAMES): ArrayObject(
                    [create_string_object(filename), filespec]
                )
            }
        )

        embedded_files_dictionary = DictionaryObject()
        embedded_files_dictionary.update(
            {NameObject("/EmbeddedFiles"): embedded_files_names_dictionary}
        )
        # Update the root
        self._root_object.update({NameObject(CA.NAMES): embedded_files_dictionary})

    def addAttachment(
        self, fname: str, fdata: Union[str, bytes]
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_attachment` instead.
        """
        deprecate_with_replacement("addAttachment", "add_attachment")
        return self.add_attachment(fname, fdata)

    def append_pages_from_reader(
        self,
        reader: PdfReader,
        after_page_append: Optional[Callable[[PageObject], None]] = None,
    ) -> None:
        """
        Copy pages from reader to writer. Includes an optional callback parameter
        which is invoked after pages are appended to the writer.

        :param PdfReader reader: a PdfReader object from which to copy page
            annotations to this writer object.  The writer's annots
            will then be updated
        :param Callable[[PageObject], None] after_page_append:
            Callback function that is invoked after each page is appended to
            the writer. Signature includes a reference to the appended page
            (delegates to append_pages_from_reader). The single parameter of the
            callback is a reference to the page just appended to the document.
        """
        # Get page count from writer and reader
        reader_num_pages = len(reader.pages)
        writer_num_pages = len(self.pages)

        # Copy pages from reader to writer
        for reader_page_number in range(reader_num_pages):
            reader_page = reader.pages[reader_page_number]
            self.add_page(reader_page)
            writer_page = self.pages[writer_num_pages + reader_page_number]
            # Trigger callback, pass writer page as parameter
            if callable(after_page_append):
                after_page_append(writer_page)

    def appendPagesFromReader(
        self,
        reader: PdfReader,
        after_page_append: Optional[Callable[[PageObject], None]] = None,
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`append_pages_from_reader` instead.
        """
        deprecate_with_replacement("appendPagesFromReader", "append_pages_from_reader")
        self.append_pages_from_reader(reader, after_page_append)

    def update_page_form_field_values(
        self,
        page: PageObject,
        fields: Dict[str, Any],
        flags: FieldFlag = OPTIONAL_READ_WRITE_FIELD,
    ) -> None:
        """
        Update the form field values for a given page from a fields dictionary.

        Copy field texts and values from fields to page.
        If the field links to a parent object, add the information to the parent.

        :param PageObject page: Page reference from PDF writer where the
            annotations and field data will be updated.
        :param dict fields: a Python dictionary of field names (/T) and text
            values (/V)
        :param int flags: An integer (0 to 7). The first bit sets ReadOnly, the
            second bit sets Required, the third bit sets NoExport. See
            PDF Reference Table 8.70 for details.
        """
        self.set_need_appearances_writer()
        # Iterate through pages, update field values
        if PG.ANNOTS not in page:
            logger_warning("No fields to update on this page", __name__)
            return
        for j in range(len(page[PG.ANNOTS])):  # type: ignore
            writer_annot = page[PG.ANNOTS][j].get_object()  # type: ignore
            # retrieve parent field values, if present
            writer_parent_annot = {}  # fallback if it's not there
            if PG.PARENT in writer_annot:
                writer_parent_annot = writer_annot[PG.PARENT]
            for field in fields:
                if writer_annot.get(FieldDictionaryAttributes.T) == field:
                    if writer_annot.get(FieldDictionaryAttributes.FT) == "/Btn":
                        writer_annot.update(
                            {
                                NameObject(
                                    AnnotationDictionaryAttributes.AS
                                ): NameObject(fields[field])
                            }
                        )
                    writer_annot.update(
                        {
                            NameObject(FieldDictionaryAttributes.V): TextStringObject(
                                fields[field]
                            )
                        }
                    )
                    if flags:
                        writer_annot.update(
                            {
                                NameObject(FieldDictionaryAttributes.Ff): NumberObject(
                                    flags
                                )
                            }
                        )
                elif writer_parent_annot.get(FieldDictionaryAttributes.T) == field:
                    writer_parent_annot.update(
                        {
                            NameObject(FieldDictionaryAttributes.V): TextStringObject(
                                fields[field]
                            )
                        }
                    )

    def updatePageFormFieldValues(
        self,
        page: PageObject,
        fields: Dict[str, Any],
        flags: FieldFlag = OPTIONAL_READ_WRITE_FIELD,
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`update_page_form_field_values` instead.
        """
        deprecate_with_replacement(
            "updatePageFormFieldValues", "update_page_form_field_values"
        )
        return self.update_page_form_field_values(page, fields, flags)

    def clone_reader_document_root(self, reader: PdfReader) -> None:
        """
        Copy the reader document root to the writer.

        :param reader:  PdfReader from the document root should be copied.
        """
        self._root_object = cast(DictionaryObject, reader.trailer[TK.ROOT])

    def cloneReaderDocumentRoot(self, reader: PdfReader) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`clone_reader_document_root` instead.
        """
        deprecate_with_replacement(
            "cloneReaderDocumentRoot", "clone_reader_document_root"
        )
        self.clone_reader_document_root(reader)

    def clone_document_from_reader(
        self,
        reader: PdfReader,
        after_page_append: Optional[Callable[[PageObject], None]] = None,
    ) -> None:
        """
        Create a copy (clone) of a document from a PDF file reader

        :param reader: PDF file reader instance from which the clone
            should be created.
        :param Callable[[PageObject], None] after_page_append:
            Callback function that is invoked after each page is appended to
            the writer. Signature includes a reference to the appended page
            (delegates to append_pages_from_reader). The single parameter of the
            callback is a reference to the page just appended to the document.
        """
        self.clone_reader_document_root(reader)
        self.append_pages_from_reader(reader, after_page_append)

    def cloneDocumentFromReader(
        self,
        reader: PdfReader,
        after_page_append: Optional[Callable[[PageObject], None]] = None,
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`clone_document_from_reader` instead.
        """
        deprecate_with_replacement(
            "cloneDocumentFromReader", "clone_document_from_reader"
        )
        self.clone_document_from_reader(reader, after_page_append)

    def encrypt(
        self,
        user_password: Optional[str] = None,
        owner_password: Optional[str] = None,
        use_128bit: bool = True,
        permissions_flag: UserAccessPermissions = ALL_DOCUMENT_PERMISSIONS,
        user_pwd: Optional[str] = None,  # deprecated
        owner_pwd: Optional[str] = None,  # deprecated
    ) -> None:
        """
        Encrypt this PDF file with the PDF Standard encryption handler.

        :param str user_password: The "user password", which allows for opening
            and reading the PDF file with the restrictions provided.
        :param str owner_password: The "owner password", which allows for
            opening the PDF files without any restrictions.  By default,
            the owner password is the same as the user password.
        :param bool use_128bit: flag as to whether to use 128bit
            encryption.  When false, 40bit encryption will be used.  By default,
            this flag is on.
        :param unsigned int permissions_flag: permissions as described in
            TABLE 3.20 of the PDF 1.7 specification. A bit value of 1 means the
            permission is grantend. Hence an integer value of -1 will set all
            flags.
            Bit position 3 is for printing, 4 is for modifying content, 5 and 6
            control annotations, 9 for form fields, 10 for extraction of
            text and graphics.
        """
        if user_pwd is not None:
            if user_password is not None:
                raise ValueError(
                    "Please only set 'user_password'. "
                    "The 'user_pwd' argument is deprecated."
                )
            else:
                warnings.warn(
                    "Please use 'user_password' instead of 'user_pwd'. "
                    "The 'user_pwd' argument is deprecated and will be removed "
                    "in PyPDF2==3.0.0."
                )
                user_password = user_pwd
        if user_password is None:  # deprecated
            # user_password is only Optional for due to the deprecated user_pwd
            raise ValueError("user_password may not be None")

        if owner_pwd is not None:  # deprecated
            if owner_password is not None:
                raise ValueError(
                    "The argument owner_pwd of encrypt is deprecated. Use owner_password only."
                )
            else:
                old_term = "owner_pwd"
                new_term = "owner_password"
                warnings.warn(
                    message=(
                        f"{old_term} is deprecated as an argument. Use {new_term} instead"
                    )
                )
                owner_password = owner_pwd

        if owner_password is None:
            owner_password = user_password
        if use_128bit:
            V = 2
            rev = 3
            keylen = int(128 / 8)
        else:
            V = 1
            rev = 2
            keylen = int(40 / 8)
        P = permissions_flag
        O = ByteStringObject(_alg33(owner_password, user_password, rev, keylen))  # type: ignore[arg-type]
        ID_1 = ByteStringObject(md5((repr(time.time())).encode("utf8")).digest())
        ID_2 = ByteStringObject(md5((repr(random.random())).encode("utf8")).digest())
        self._ID = ArrayObject((ID_1, ID_2))
        if rev == 2:
            U, key = _alg34(user_password, O, P, ID_1)
        else:
            assert rev == 3
            U, key = _alg35(user_password, rev, keylen, O, P, ID_1, False)  # type: ignore[arg-type]
        encrypt = DictionaryObject()
        encrypt[NameObject(SA.FILTER)] = NameObject("/Standard")
        encrypt[NameObject("/V")] = NumberObject(V)
        if V == 2:
            encrypt[NameObject(SA.LENGTH)] = NumberObject(keylen * 8)
        encrypt[NameObject(ED.R)] = NumberObject(rev)
        encrypt[NameObject(ED.O)] = ByteStringObject(O)
        encrypt[NameObject(ED.U)] = ByteStringObject(U)
        encrypt[NameObject(ED.P)] = NumberObject(P)
        self._encrypt = self._add_object(encrypt)
        self._encrypt_key = key

    def write_stream(self, stream: StreamType) -> None:
        if hasattr(stream, "mode") and "b" not in stream.mode:
            logger_warning(
                f"File <{stream.name}> to write to is not in binary mode. "  # type: ignore
                "It may not be written to correctly.",
                __name__,
            )

        if not self._root:
            self._root = self._add_object(self._root_object)

        # PDF objects sometimes have circular references to their /Page objects
        # inside their object tree (for example, annotations).  Those will be
        # indirect references to objects that we've recreated in this PDF.  To
        # address this problem, PageObject's store their original object
        # reference number, and we add it to the external reference map before
        # we sweep for indirect references.  This forces self-page-referencing
        # trees to reference the correct new object location, rather than
        # copying in a new copy of the page object.
        self._sweep_indirect_references(self._root)

        object_positions = self._write_header(stream)
        xref_location = self._write_xref_table(stream, object_positions)
        self._write_trailer(stream)
        stream.write(b_(f"\nstartxref\n{xref_location}\n%%EOF\n"))  # eof

    def write(
        self, stream: Union[Path, StrByteType]
    ) -> Tuple[bool, Union[FileIO, BytesIO, BufferedReader, BufferedWriter]]:
        """
        Write the collection of pages added to this object out as a PDF file.

        :param stream: An object to write the file to.  The object can support
            the write method and the tell method, similar to a file object, or
            be a file path, just like the fileobj, just named it stream to keep
            existing workflow.
        """
        my_file = False

        if stream == "":
            raise ValueError(f"Output(stream={stream}) is empty.")

        if isinstance(stream, (str, Path)):
            stream = FileIO(stream, "wb")
            my_file = True

        self.write_stream(stream)

        if self.with_as_usage:
            stream.close()

        return my_file, stream

    def _write_header(self, stream: StreamType) -> List[int]:
        object_positions = []
        stream.write(self.pdf_header + b"\n")
        stream.write(b"%\xE2\xE3\xCF\xD3\n")
        for i, obj in enumerate(self._objects):
            obj = self._objects[i]
            # If the obj is None we can't write anything
            if obj is not None:
                idnum = i + 1
                object_positions.append(stream.tell())
                stream.write(b_(str(idnum)) + b" 0 obj\n")
                key = None
                if hasattr(self, "_encrypt") and idnum != self._encrypt.idnum:
                    pack1 = struct.pack("<i", i + 1)[:3]
                    pack2 = struct.pack("<i", 0)[:2]
                    key = self._encrypt_key + pack1 + pack2
                    assert len(key) == (len(self._encrypt_key) + 5)
                    md5_hash = md5(key).digest()
                    key = md5_hash[: min(16, len(self._encrypt_key) + 5)]
                obj.write_to_stream(stream, key)
                stream.write(b"\nendobj\n")
        return object_positions

    def _write_xref_table(self, stream: StreamType, object_positions: List[int]) -> int:
        xref_location = stream.tell()
        stream.write(b"xref\n")
        stream.write(b_(f"0 {len(self._objects) + 1}\n"))
        stream.write(b_(f"{0:0>10} {65535:0>5} f \n"))
        for offset in object_positions:
            stream.write(b_(f"{offset:0>10} {0:0>5} n \n"))
        return xref_location

    def _write_trailer(self, stream: StreamType) -> None:
        stream.write(b"trailer\n")
        trailer = DictionaryObject()
        trailer.update(
            {
                NameObject(TK.SIZE): NumberObject(len(self._objects) + 1),
                NameObject(TK.ROOT): self._root,
                NameObject(TK.INFO): self._info,
            }
        )
        if hasattr(self, "_ID"):
            trailer[NameObject(TK.ID)] = self._ID
        if hasattr(self, "_encrypt"):
            trailer[NameObject(TK.ENCRYPT)] = self._encrypt
        trailer.write_to_stream(stream, None)

    def add_metadata(self, infos: Dict[str, Any]) -> None:
        """
        Add custom metadata to the output.

        :param dict infos: a Python dictionary where each key is a field
            and each value is your new metadata.
        """
        args = {}
        for key, value in list(infos.items()):
            args[NameObject(key)] = create_string_object(value)
        self.get_object(self._info).update(args)  # type: ignore

    def addMetadata(self, infos: Dict[str, Any]) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_metadata` instead.
        """
        deprecate_with_replacement("addMetadata", "add_metadata")
        self.add_metadata(infos)

    def _sweep_indirect_references(
        self,
        root: Union[
            ArrayObject,
            BooleanObject,
            DictionaryObject,
            FloatObject,
            IndirectObject,
            NameObject,
            PdfObject,
            NumberObject,
            TextStringObject,
            NullObject,
        ],
    ) -> None:
        stack: Deque[
            Tuple[
                Any,
                Optional[Any],
                Any,
                List[PdfObject],
            ]
        ] = collections.deque()
        discovered = []
        parent = None
        grant_parents: List[PdfObject] = []
        key_or_id = None

        # Start from root
        stack.append((root, parent, key_or_id, grant_parents))

        while len(stack):
            data, parent, key_or_id, grant_parents = stack.pop()

            # Build stack for a processing depth-first
            if isinstance(data, (ArrayObject, DictionaryObject)):
                for key, value in data.items():
                    stack.append(
                        (
                            value,
                            data,
                            key,
                            grant_parents + [parent] if parent is not None else [],
                        )
                    )
            elif isinstance(data, IndirectObject):
                data = self._resolve_indirect_object(data)

                if str(data) not in discovered:
                    discovered.append(str(data))
                    stack.append((data.get_object(), None, None, []))

            # Check if data has a parent and if it is a dict or an array update the value
            if isinstance(parent, (DictionaryObject, ArrayObject)):
                if isinstance(data, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    data = self._resolve_indirect_object(self._add_object(data))

                update_hashes = []

                # Data changed and thus the hash value changed
                if parent[key_or_id] != data:
                    update_hashes = [parent.hash_value()] + [
                        grant_parent.hash_value() for grant_parent in grant_parents
                    ]
                    parent[key_or_id] = data

                # Update old hash value to new hash value
                for old_hash in update_hashes:
                    indirect_reference = self._idnum_hash.pop(old_hash, None)

                    if indirect_reference is not None:
                        indirect_reference_obj = indirect_reference.get_object()

                        if indirect_reference_obj is not None:
                            self._idnum_hash[
                                indirect_reference_obj.hash_value()
                            ] = indirect_reference

    def _resolve_indirect_object(self, data: IndirectObject) -> IndirectObject:
        """
        Resolves indirect object to this pdf indirect objects.

        If it is a new object then it is added to self._objects
        and new idnum is given and generation is always 0.
        """
        if hasattr(data.pdf, "stream") and data.pdf.stream.closed:
            raise ValueError(f"I/O operation on closed file: {data.pdf.stream.name}")

        # Get real object indirect object
        real_obj = data.pdf.get_object(data)

        if real_obj is None:
            logger_warning(
                f"Unable to resolve [{data.__class__.__name__}: {data}], "
                "returning NullObject instead",
                __name__,
            )
            real_obj = NullObject()

        hash_value = real_obj.hash_value()

        # Check if object is handled
        if hash_value in self._idnum_hash:
            return self._idnum_hash[hash_value]

        if data.pdf == self:
            self._idnum_hash[hash_value] = IndirectObject(data.idnum, 0, self)
        # This is new object in this pdf
        else:
            self._idnum_hash[hash_value] = self._add_object(real_obj)

        return self._idnum_hash[hash_value]

    def get_reference(self, obj: PdfObject) -> IndirectObject:
        idnum = self._objects.index(obj) + 1
        ref = IndirectObject(idnum, 0, self)
        assert ref.get_object() == obj
        return ref

    def getReference(self, obj: PdfObject) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`get_reference` instead.
        """
        deprecate_with_replacement("getReference", "get_reference")
        return self.get_reference(obj)

    def get_outline_root(self) -> TreeObject:
        if CO.OUTLINES in self._root_object:
            # TABLE 3.25 Entries in the catalog dictionary
            outline = cast(TreeObject, self._root_object[CO.OUTLINES])
            idnum = self._objects.index(outline) + 1
            outline_ref = IndirectObject(idnum, 0, self)
            assert outline_ref.get_object() == outline
        else:
            outline = TreeObject()
            outline.update({})
            outline_ref = self._add_object(outline)
            self._root_object[NameObject(CO.OUTLINES)] = outline_ref

        return outline

    def get_threads_root(self) -> ArrayObject:
        """
        the list of threads see §8.3.2 from PDF 1.7 spec

                :return: an Array (possibly empty) of Dictionaries with "/F" and "/I" properties
        """
        if CO.THREADS in self._root_object:
            # TABLE 3.25 Entries in the catalog dictionary
            threads = cast(ArrayObject, self._root_object[CO.THREADS])
        else:
            threads = ArrayObject()
            self._root_object[NameObject(CO.THREADS)] = threads
        return threads

    @property
    def threads(self) -> ArrayObject:
        """
        Read-only property for the list of threads see §8.3.2 from PDF 1.7 spec

        :return: an Array (possibly empty) of Dictionaries with "/F" and "/I" properties
        """
        return self.get_threads_root()

    def getOutlineRoot(self) -> TreeObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`get_outline_root` instead.
        """
        deprecate_with_replacement("getOutlineRoot", "get_outline_root")
        return self.get_outline_root()

    def get_named_dest_root(self) -> ArrayObject:
        if CA.NAMES in self._root_object and isinstance(
            self._root_object[CA.NAMES], DictionaryObject
        ):
            names = cast(DictionaryObject, self._root_object[CA.NAMES])
            idnum = self._objects.index(names) + 1
            names_ref = IndirectObject(idnum, 0, self)
            assert names_ref.get_object() == names
            if CA.DESTS in names and isinstance(names[CA.DESTS], DictionaryObject):
                # 3.6.3 Name Dictionary (PDF spec 1.7)
                dests = cast(DictionaryObject, names[CA.DESTS])
                idnum = self._objects.index(dests) + 1
                dests_ref = IndirectObject(idnum, 0, self)
                assert dests_ref.get_object() == dests
                if CA.NAMES in dests:
                    # TABLE 3.33 Entries in a name tree node dictionary
                    nd = cast(ArrayObject, dests[CA.NAMES])
                else:
                    nd = ArrayObject()
                    dests[NameObject(CA.NAMES)] = nd
            else:
                dests = DictionaryObject()
                dests_ref = self._add_object(dests)
                names[NameObject(CA.DESTS)] = dests_ref
                nd = ArrayObject()
                dests[NameObject(CA.NAMES)] = nd

        else:
            names = DictionaryObject()
            names_ref = self._add_object(names)
            self._root_object[NameObject(CA.NAMES)] = names_ref
            dests = DictionaryObject()
            dests_ref = self._add_object(dests)
            names[NameObject(CA.DESTS)] = dests_ref
            nd = ArrayObject()
            dests[NameObject(CA.NAMES)] = nd

        return nd

    def getNamedDestRoot(self) -> ArrayObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`get_named_dest_root` instead.
        """
        deprecate_with_replacement("getNamedDestRoot", "get_named_dest_root")
        return self.get_named_dest_root()

    def add_outline_item_destination(
        self,
        page_destination: Union[None, PageObject, TreeObject] = None,
        parent: Union[None, TreeObject, IndirectObject] = None,
        dest: Union[None, PageObject, TreeObject] = None,   # deprecated
    ) -> IndirectObject:
        if page_destination is not None and dest is not None:  # deprecated
            raise ValueError(
                "The argument dest of add_outline_item_destination is deprecated. Use page_destination only."
            )
        if dest is not None:  # deprecated
            old_term = "dest"
            new_term = "page_destination"
            warnings.warn(
                message=(
                    f"{old_term} is deprecated as an argument. Use {new_term} instead"
                )
            )
            page_destination = dest
        if page_destination is None:  # deprecated
            # argument is only Optional due to deprecated argument.
            raise ValueError("page_destination may not be None")

        if parent is None:
            parent = self.get_outline_root()

        parent = cast(TreeObject, parent.get_object())
        page_destination_ref = self._add_object(page_destination)
        parent.add_child(page_destination_ref, self)

        return page_destination_ref

    def add_bookmark_destination(
        self,
        dest: Union[PageObject, TreeObject],
        parent: Union[None, TreeObject, IndirectObject] = None,
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 2.9.0

            Use :meth:`add_outline_item_destination` instead.
        """
        deprecate_with_replacement(
            "add_bookmark_destination", "add_outline_item_destination"
        )
        return self.add_outline_item_destination(dest, parent)

    def addBookmarkDestination(
        self, dest: PageObject, parent: Optional[TreeObject] = None
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_outline_item_destination` instead.
        """
        deprecate_with_replacement(
            "addBookmarkDestination", "add_outline_item_destination"
        )
        return self.add_outline_item_destination(dest, parent)

    @deprecate_bookmark(bookmark="outline_item")
    def add_outline_item_dict(
        self, outline_item: OutlineItemType, parent: Optional[TreeObject] = None
    ) -> IndirectObject:
        outline_item_object = TreeObject()
        for k, v in list(outline_item.items()):
            outline_item_object[NameObject(str(k))] = v
        outline_item_object.update(outline_item)

        if "/A" in outline_item:
            action = DictionaryObject()
            a_dict = cast(DictionaryObject, outline_item["/A"])
            for k, v in list(a_dict.items()):
                action[NameObject(str(k))] = v
            action_ref = self._add_object(action)
            outline_item_object[NameObject("/A")] = action_ref

        return self.add_outline_item_destination(outline_item_object, parent)

    @deprecate_bookmark(bookmark="outline_item")
    def add_bookmark_dict(
        self, outline_item: OutlineItemType, parent: Optional[TreeObject] = None
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 2.9.0

            Use :meth:`add_outline_item_dict` instead.
        """
        deprecate_with_replacement("add_bookmark_dict", "add_outline_item_dict")
        return self.add_outline_item_dict(outline_item, parent)

    @deprecate_bookmark(bookmark="outline_item")
    def addBookmarkDict(
        self, outline_item: OutlineItemType, parent: Optional[TreeObject] = None
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_outline_item_dict` instead.
        """
        deprecate_with_replacement("addBookmarkDict", "add_outline_item_dict")
        return self.add_outline_item_dict(outline_item, parent)

    def add_outline_item(
        self,
        title: str,
        page_number: Optional[int] = None,
        parent: Union[None, TreeObject, IndirectObject] = None,
        color: Optional[Union[Tuple[float, float, float], str]] = None,
        bold: bool = False,
        italic: bool = False,
        fit: FitType = "/Fit",
        *args: ZoomArgType,
        pagenum: Optional[int] = None,  # deprecated
    ) -> IndirectObject:
        """
        Add an outline item (commonly referred to as a "Bookmark") to this PDF file.

        :param str title: Title to use for this outline item.
        :param int page_number: Page number this outline item will point to.
        :param parent: A reference to a parent outline item to create nested
            outline items.
        :param tuple color: Color of the outline item's font as a red, green, blue tuple
            from 0.0 to 1.0 or as a Hex String (#RRGGBB)
        :param bool bold: Outline item font is bold
        :param bool italic: Outline item font is italic
        :param str fit: The fit of the destination page. See
            :meth:`add_link()<add_link>` for details.
        """
        if page_number is not None and pagenum is not None:
            raise ValueError(
                "The argument pagenum of add_outline_item is deprecated. Use page_number only."
            )
        if pagenum is not None:
            old_term = "pagenum"
            new_term = "page_number"
            warnings.warn(
                message=(
                    f"{old_term} is deprecated as an argument. Use {new_term} instead"
                )
            )
            page_number = pagenum
        if page_number is None:
            raise ValueError("page_number may not be None")
        page_ref = NumberObject(page_number)
        zoom_args: ZoomArgsType = [
            NullObject() if a is None else NumberObject(a) for a in args
        ]
        dest = Destination(
            NameObject("/" + title + " outline item"),
            page_ref,
            NameObject(fit),
            *zoom_args,
        )

        action_ref = self._add_object(
            DictionaryObject(
                {
                    NameObject(GoToActionArguments.D): dest.dest_array,
                    NameObject(GoToActionArguments.S): NameObject("/GoTo"),
                }
            )
        )
        outline_item = _create_outline_item(action_ref, title, color, italic, bold)

        if parent is None:
            parent = self.get_outline_root()
        return self.add_outline_item_destination(outline_item, parent)

    def add_bookmark(
        self,
        title: str,
        pagenum: int,  # deprecated, but the whole method is deprecated
        parent: Union[None, TreeObject, IndirectObject] = None,
        color: Optional[Tuple[float, float, float]] = None,
        bold: bool = False,
        italic: bool = False,
        fit: FitType = "/Fit",
        *args: ZoomArgType,
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 2.9.0

            Use :meth:`add_outline_item` instead.
        """
        deprecate_with_replacement("add_bookmark", "add_outline_item")
        return self.add_outline_item(
            title, pagenum, parent, color, bold, italic, fit, *args
        )

    def addBookmark(
        self,
        title: str,
        pagenum: int,
        parent: Union[None, TreeObject, IndirectObject] = None,
        color: Optional[Tuple[float, float, float]] = None,
        bold: bool = False,
        italic: bool = False,
        fit: FitType = "/Fit",
        *args: ZoomArgType,
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_outline_item` instead.
        """
        deprecate_with_replacement("addBookmark", "add_outline_item")
        return self.add_outline_item(
            title, pagenum, parent, color, bold, italic, fit, *args
        )

    def add_outline(self) -> None:
        raise NotImplementedError(
            "This method is not yet implemented. Use :meth:`add_outline_item` instead."
        )

    def add_named_destination_object(
        self,
        page_destination: Optional[PdfObject] = None,
        dest: Optional[PdfObject] = None,
    ) -> IndirectObject:
        if page_destination is not None and dest is not None:
            raise ValueError(
                "The argument dest of add_named_destination_object is deprecated. Use page_destination only."
            )
        if dest is not None:  # deprecated
            old_term = "dest"
            new_term = "page_destination"
            warnings.warn(
                message=(
                    f"{old_term} is deprecated as an argument. Use {new_term} instead"
                )
            )
            page_destination = dest
        if page_destination is None:  # deprecated
            raise ValueError("page_destination may not be None")

        page_destination_ref = self._add_object(page_destination)

        nd = self.get_named_dest_root()
        nd.extend([page_destination["/Title"], page_destination_ref])  # type: ignore
        return page_destination_ref

    def addNamedDestinationObject(
        self, dest: PdfObject
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_named_destination_object` instead.
        """
        deprecate_with_replacement(
            "addNamedDestinationObject", "add_named_destination_object"
        )
        return self.add_named_destination_object(dest)

    def add_named_destination(
        self,
        title: str,
        page_number: Optional[int] = None,
        pagenum: Optional[int] = None,  # deprecated
    ) -> IndirectObject:
        if page_number is not None and pagenum is not None:
            raise ValueError(
                "The argument pagenum of add_outline_item is deprecated. Use page_number only."
            )
        if pagenum is not None:
            old_term = "pagenum"
            new_term = "page_number"
            warnings.warn(
                message=(
                    f"{old_term} is deprecated as an argument. Use {new_term} instead"
                )
            )
            page_number = pagenum
        if page_number is None:
            raise ValueError("page_number may not be None")
        page_ref = self.get_object(self._pages)[PA.KIDS][page_number]  # type: ignore
        dest = DictionaryObject()
        dest.update(
            {
                NameObject(GoToActionArguments.D): ArrayObject(
                    [page_ref, NameObject(TypFitArguments.FIT_H), NumberObject(826)]
                ),
                NameObject(GoToActionArguments.S): NameObject("/GoTo"),
            }
        )

        dest_ref = self._add_object(dest)
        nd = self.get_named_dest_root()
        nd.extend([title, dest_ref])
        return dest_ref

    def addNamedDestination(
        self, title: str, pagenum: int
    ) -> IndirectObject:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_named_destination` instead.
        """
        deprecate_with_replacement("addNamedDestination", "add_named_destination")
        return self.add_named_destination(title, pagenum)

    def remove_links(self) -> None:
        """Remove links and annotations from this output."""
        pg_dict = cast(DictionaryObject, self.get_object(self._pages))
        pages = cast(ArrayObject, pg_dict[PA.KIDS])
        for page in pages:
            page_ref = cast(DictionaryObject, self.get_object(page))
            if PG.ANNOTS in page_ref:
                del page_ref[PG.ANNOTS]

    def removeLinks(self) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`remove_links` instead.
        """
        deprecate_with_replacement("removeLinks", "remove_links")
        return self.remove_links()

    def remove_images(self, ignore_byte_string_object: bool = False) -> None:
        """
        Remove images from this output.

        :param bool ignore_byte_string_object: optional parameter
            to ignore ByteString Objects.
        """
        pg_dict = cast(DictionaryObject, self.get_object(self._pages))
        pages = cast(ArrayObject, pg_dict[PA.KIDS])
        jump_operators = (
            b"cm",
            b"w",
            b"J",
            b"j",
            b"M",
            b"d",
            b"ri",
            b"i",
            b"gs",
            b"W",
            b"b",
            b"s",
            b"S",
            b"f",
            b"F",
            b"n",
            b"m",
            b"l",
            b"c",
            b"v",
            b"y",
            b"h",
            b"B",
            b"Do",
            b"sh",
        )
        for page in pages:
            page_ref = cast(DictionaryObject, self.get_object(page))
            content = page_ref["/Contents"].get_object()
            if not isinstance(content, ContentStream):
                content = ContentStream(content, page_ref)

            _operations = []
            seq_graphics = False
            for operands, operator in content.operations:
                if operator in [b"Tj", b"'"]:
                    text = operands[0]
                    if ignore_byte_string_object and not isinstance(
                        text, TextStringObject
                    ):
                        operands[0] = TextStringObject()
                elif operator == b'"':
                    text = operands[2]
                    if ignore_byte_string_object and not isinstance(
                        text, TextStringObject
                    ):
                        operands[2] = TextStringObject()
                elif operator == b"TJ":
                    for i in range(len(operands[0])):
                        if ignore_byte_string_object and not isinstance(
                            operands[0][i], TextStringObject
                        ):
                            operands[0][i] = TextStringObject()

                if operator == b"q":
                    seq_graphics = True
                if operator == b"Q":
                    seq_graphics = False
                if seq_graphics and operator in jump_operators:
                    continue
                if operator == b"re":
                    continue
                _operations.append((operands, operator))

            content.operations = _operations
            page_ref.__setitem__(NameObject("/Contents"), content)

    def removeImages(
        self, ignoreByteStringObject: bool = False
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`remove_images` instead.
        """
        deprecate_with_replacement("removeImages", "remove_images")
        return self.remove_images(ignoreByteStringObject)

    def remove_text(self, ignore_byte_string_object: bool = False) -> None:
        """
        Remove text from this output.

        :param bool ignore_byte_string_object: optional parameter
            to ignore ByteString Objects.
        """
        pg_dict = cast(DictionaryObject, self.get_object(self._pages))
        pages = cast(List[IndirectObject], pg_dict[PA.KIDS])
        for page in pages:
            page_ref = cast(PageObject, self.get_object(page))
            content = page_ref["/Contents"].get_object()
            if not isinstance(content, ContentStream):
                content = ContentStream(content, page_ref)
            for operands, operator in content.operations:
                if operator in [b"Tj", b"'"]:
                    text = operands[0]
                    if not ignore_byte_string_object:
                        if isinstance(text, TextStringObject):
                            operands[0] = TextStringObject()
                    else:
                        if isinstance(text, (TextStringObject, ByteStringObject)):
                            operands[0] = TextStringObject()
                elif operator == b'"':
                    text = operands[2]
                    if not ignore_byte_string_object:
                        if isinstance(text, TextStringObject):
                            operands[2] = TextStringObject()
                    else:
                        if isinstance(text, (TextStringObject, ByteStringObject)):
                            operands[2] = TextStringObject()
                elif operator == b"TJ":
                    for i in range(len(operands[0])):
                        if not ignore_byte_string_object:
                            if isinstance(operands[0][i], TextStringObject):
                                operands[0][i] = TextStringObject()
                        else:
                            if isinstance(
                                operands[0][i], (TextStringObject, ByteStringObject)
                            ):
                                operands[0][i] = TextStringObject()

            page_ref.__setitem__(NameObject("/Contents"), content)

    def removeText(
        self, ignoreByteStringObject: bool = False
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`remove_text` instead.
        """
        deprecate_with_replacement("removeText", "remove_text")
        return self.remove_text(ignoreByteStringObject)

    def add_uri(
        self,
        page_number: int,
        uri: str,
        rect: RectangleObject,
        border: Optional[ArrayObject] = None,
        pagenum: Optional[int] = None,
    ) -> None:
        """
        Add an URI from a rectangular area to the specified page.
        This uses the basic structure of :meth:`add_link`

        :param int page_number: index of the page on which to place the URI action.
        :param str uri: URI of resource to link to.
        :param Tuple[int, int, int, int] rect: :class:`RectangleObject<PyPDF2.generic.RectangleObject>` or array of four
            integers specifying the clickable rectangular area
            ``[xLL, yLL, xUR, yUR]``, or string in the form ``"[ xLL yLL xUR yUR ]"``.
        :param ArrayObject border: if provided, an array describing border-drawing
            properties. See the PDF spec for details. No border will be
            drawn if this argument is omitted.
        """
        if pagenum is not None:
            warnings.warn(
                "The 'pagenum' argument of add_uri is deprecated. Use 'page_number' instead."
            )
            page_number = pagenum
        page_link = self.get_object(self._pages)[PA.KIDS][page_number]  # type: ignore
        page_ref = cast(Dict[str, Any], self.get_object(page_link))

        border_arr: BorderArrayType
        if border is not None:
            border_arr = [NameObject(n) for n in border[:3]]
            if len(border) == 4:
                dash_pattern = ArrayObject([NameObject(n) for n in border[3]])
                border_arr.append(dash_pattern)
        else:
            border_arr = [NumberObject(2)] * 3

        if isinstance(rect, str):
            rect = NameObject(rect)
        elif isinstance(rect, RectangleObject):
            pass
        else:
            rect = RectangleObject(rect)

        lnk2 = DictionaryObject()
        lnk2.update(
            {
                NameObject("/S"): NameObject("/URI"),
                NameObject("/URI"): TextStringObject(uri),
            }
        )
        lnk = DictionaryObject()
        lnk.update(
            {
                NameObject(AnnotationDictionaryAttributes.Type): NameObject(PG.ANNOTS),
                NameObject(AnnotationDictionaryAttributes.Subtype): NameObject("/Link"),
                NameObject(AnnotationDictionaryAttributes.P): page_link,
                NameObject(AnnotationDictionaryAttributes.Rect): rect,
                NameObject("/H"): NameObject("/I"),
                NameObject(AnnotationDictionaryAttributes.Border): ArrayObject(
                    border_arr
                ),
                NameObject("/A"): lnk2,
            }
        )
        lnk_ref = self._add_object(lnk)

        if PG.ANNOTS in page_ref:
            page_ref[PG.ANNOTS].append(lnk_ref)
        else:
            page_ref[NameObject(PG.ANNOTS)] = ArrayObject([lnk_ref])

    def addURI(
        self,
        pagenum: int,  # deprecated, but method is deprecated already
        uri: str,
        rect: RectangleObject,
        border: Optional[ArrayObject] = None,
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_uri` instead.
        """
        deprecate_with_replacement("addURI", "add_uri")
        return self.add_uri(pagenum, uri, rect, border)

    def add_link(
        self,
        pagenum: int,  # deprecated, but method is deprecated already
        page_destination: int,
        rect: RectangleObject,
        border: Optional[ArrayObject] = None,
        fit: FitType = "/Fit",
        *args: ZoomArgType,
    ) -> None:
        deprecate_with_replacement(
            "add_link", "add_annotation(AnnotationBuilder.link(...))"
        )

        if isinstance(rect, str):
            rect = rect.strip()[1:-1]
            rect = RectangleObject(
                [float(num) for num in rect.split(" ") if len(num) > 0]
            )
        elif isinstance(rect, RectangleObject):
            pass
        else:
            rect = RectangleObject(rect)

        annotation = AnnotationBuilder.link(
            rect=rect,
            border=border,
            target_page_index=page_destination,
            fit=fit,
            fit_args=args,
        )
        return self.add_annotation(page_number=pagenum, annotation=annotation)

    def addLink(
        self,
        pagenum: int,  # deprecated, but method is deprecated already
        page_destination: int,
        rect: RectangleObject,
        border: Optional[ArrayObject] = None,
        fit: FitType = "/Fit",
        *args: ZoomArgType,
    ) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :meth:`add_link` instead.
        """
        deprecate_with_replacement(
            "addLink", "add_annotation(AnnotationBuilder.link(...))", "4.0.0"
        )
        return self.add_link(pagenum, page_destination, rect, border, fit, *args)

    _valid_layouts = (
        "/NoLayout",
        "/SinglePage",
        "/OneColumn",
        "/TwoColumnLeft",
        "/TwoColumnRight",
        "/TwoPageLeft",
        "/TwoPageRight",
    )

    def _get_page_layout(self) -> Optional[LayoutType]:
        try:
            return cast(LayoutType, self._root_object["/PageLayout"])
        except KeyError:
            return None

    def getPageLayout(self) -> Optional[LayoutType]:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_layout` instead.
        """
        deprecate_with_replacement("getPageLayout", "page_layout")
        return self._get_page_layout()

    def _set_page_layout(self, layout: Union[NameObject, LayoutType]) -> None:
        """
        Set the page layout.

        :param str layout: The page layout to be used.

        .. list-table:: Valid ``layout`` arguments
           :widths: 50 200

           * - /NoLayout
             - Layout explicitly not specified
           * - /SinglePage
             - Show one page at a time
           * - /OneColumn
             - Show one column at a time
           * - /TwoColumnLeft
             - Show pages in two columns, odd-numbered pages on the left
           * - /TwoColumnRight
             - Show pages in two columns, odd-numbered pages on the right
           * - /TwoPageLeft
             - Show two pages at a time, odd-numbered pages on the left
           * - /TwoPageRight
             - Show two pages at a time, odd-numbered pages on the right
        """
        if not isinstance(layout, NameObject):
            if layout not in self._valid_layouts:
                logger_warning(
                    f"Layout should be one of: {'', ''.join(self._valid_layouts)}",
                    __name__,
                )
            layout = NameObject(layout)
        self._root_object.update({NameObject("/PageLayout"): layout})

    def setPageLayout(self, layout: LayoutType) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_layout` instead.
        """
        deprecate_with_replacement(
            "writer.setPageLayout(val)", "writer.page_layout = val"
        )
        return self._set_page_layout(layout)

    @property
    def page_layout(self) -> Optional[LayoutType]:
        """
        Page layout property.

        .. list-table:: Valid ``layout`` values
           :widths: 50 200

           * - /NoLayout
             - Layout explicitly not specified
           * - /SinglePage
             - Show one page at a time
           * - /OneColumn
             - Show one column at a time
           * - /TwoColumnLeft
             - Show pages in two columns, odd-numbered pages on the left
           * - /TwoColumnRight
             - Show pages in two columns, odd-numbered pages on the right
           * - /TwoPageLeft
             - Show two pages at a time, odd-numbered pages on the left
           * - /TwoPageRight
             - Show two pages at a time, odd-numbered pages on the right
        """
        return self._get_page_layout()

    @page_layout.setter
    def page_layout(self, layout: LayoutType) -> None:
        self._set_page_layout(layout)

    @property
    def pageLayout(self) -> Optional[LayoutType]:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_layout` instead.
        """
        deprecate_with_replacement("pageLayout", "page_layout")
        return self.page_layout

    @pageLayout.setter
    def pageLayout(self, layout: LayoutType) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_layout` instead.
        """
        deprecate_with_replacement("pageLayout", "page_layout")
        self.page_layout = layout

    _valid_modes = (
        "/UseNone",
        "/UseOutlines",
        "/UseThumbs",
        "/FullScreen",
        "/UseOC",
        "/UseAttachments",
    )

    def _get_page_mode(self) -> Optional[PagemodeType]:
        try:
            return cast(PagemodeType, self._root_object["/PageMode"])
        except KeyError:
            return None

    def getPageMode(self) -> Optional[PagemodeType]:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_mode` instead.
        """
        deprecate_with_replacement("getPageMode", "page_mode")
        return self._get_page_mode()

    def set_page_mode(self, mode: PagemodeType) -> None:
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_mode` instead.
        """
        if isinstance(mode, NameObject):
            mode_name: NameObject = mode
        else:
            if mode not in self._valid_modes:
                logger_warning(
                    f"Mode should be one of: {', '.join(self._valid_modes)}", __name__
                )
            mode_name = NameObject(mode)
        self._root_object.update({NameObject("/PageMode"): mode_name})

    def setPageMode(self, mode: PagemodeType) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_mode` instead.
        """
        deprecate_with_replacement("writer.setPageMode(val)", "writer.page_mode = val")
        self.set_page_mode(mode)

    @property
    def page_mode(self) -> Optional[PagemodeType]:
        """
        Page mode property.

        .. list-table:: Valid ``mode`` values
           :widths: 50 200

           * - /UseNone
             - Do not show outline or thumbnails panels
           * - /UseOutlines
             - Show outline (aka bookmarks) panel
           * - /UseThumbs
             - Show page thumbnails panel
           * - /FullScreen
             - Fullscreen view
           * - /UseOC
             - Show Optional Content Group (OCG) panel
           * - /UseAttachments
             - Show attachments panel
        """
        return self._get_page_mode()

    @page_mode.setter
    def page_mode(self, mode: PagemodeType) -> None:
        self.set_page_mode(mode)

    @property
    def pageMode(self) -> Optional[PagemodeType]:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_mode` instead.
        """
        deprecate_with_replacement("pageMode", "page_mode")
        return self.page_mode

    @pageMode.setter
    def pageMode(self, mode: PagemodeType) -> None:  # pragma: no cover
        """
        .. deprecated:: 1.28.0

            Use :py:attr:`page_mode` instead.
        """
        deprecate_with_replacement("pageMode", "page_mode")
        self.page_mode = mode

    def add_annotation(self, page_number: int, annotation: Dict[str, Any]) -> None:
        to_add = cast(DictionaryObject, _pdf_objectify(annotation))
        to_add[NameObject("/P")] = self.get_object(self._pages)["/Kids"][page_number]  # type: ignore
        page = self.pages[page_number]
        if page.annotations is None:
            page[NameObject("/Annots")] = ArrayObject()
        assert page.annotations is not None

        # Internal link annotations need the correct object type for the
        # destination
        if to_add.get("/Subtype") == "/Link" and NameObject("/Dest") in to_add:
            tmp = cast(dict, to_add[NameObject("/Dest")])
            dest = Destination(
                NameObject("/LinkName"),
                tmp["target_page_index"],
                tmp["fit"],
                *tmp["fit_args"],
            )
            to_add[NameObject("/Dest")] = dest.dest_array

        ind_obj = self._add_object(to_add)

        page.annotations.append(ind_obj)


def _pdf_objectify(obj: Union[Dict[str, Any], str, int, List[Any]]) -> PdfObject:
    if isinstance(obj, PdfObject):
        return obj
    if isinstance(obj, dict):
        to_add = DictionaryObject()
        for key, value in obj.items():
            name_key = NameObject(key)
            casted_value = _pdf_objectify(value)
            to_add[name_key] = casted_value
        return to_add
    elif isinstance(obj, list):
        arr = ArrayObject()
        for el in obj:
            arr.append(_pdf_objectify(el))
        return arr
    elif isinstance(obj, str):
        if obj.startswith("/"):
            return NameObject(obj)
        else:
            return TextStringObject(obj)
    elif isinstance(obj, (int, float)):
        return FloatObject(obj)
    else:
        raise NotImplementedError(
            f"type(obj)={type(obj)} could not be casted to PdfObject"
        )


def _create_outline_item(
    action_ref: IndirectObject,
    title: str,
    color: Union[Tuple[float, float, float], str, None],
    italic: bool,
    bold: bool,
) -> TreeObject:
    outline_item = TreeObject()
    outline_item.update(
        {
            NameObject("/A"): action_ref,
            NameObject("/Title"): create_string_object(title),
        }
    )
    if color:
        if isinstance(color, str):
            color = hex_to_rgb(color)
        prec = decimal.Decimal("1.00000")
        outline_item.update(
            {
                NameObject("/C"): ArrayObject(
                    [FloatObject(decimal.Decimal(c).quantize(prec)) for c in color]
                )
            }
        )
    if italic or bold:
        format_flag = 0
        if italic:
            format_flag += 1
        if bold:
            format_flag += 2
        outline_item.update({NameObject("/F"): NumberObject(format_flag)})
    return outline_item


class PdfFileWriter(PdfWriter):  # pragma: no cover
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        deprecate_with_replacement("PdfFileWriter", "PdfWriter")
        super().__init__(*args, **kwargs)
