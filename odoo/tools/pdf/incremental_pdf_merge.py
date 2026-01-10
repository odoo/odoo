# Copyright (c) 2006-2008, Mathieu Fenniak
# Some contributions copyright (c) 2007, Ashish Kulkarni <kulkarni.ashish@gmail.com>
# Some contributions copyright (c) 2014, Steve Witham <switham_github@mac-guyver.com>
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


import io
import logging
from collections import deque
import uuid
from typing import (
    Any,
    Dict,
    Tuple,
    cast,
)

from odoo.tools.pdf import (
    PdfFileReader,
    PdfFileWriter,
    IndirectObject,
    NullObject,
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    FloatObject,
    ContentStream,
    DecodedStreamObject as StreamObject,
)

from .constants import TrailerKeys as TK, Resources as RES, PageAttributes as PG

_logger = logging.getLogger(__name__)

_B_CACHE = {}
def b_(s: str | bytes) -> bytes:
    """
    Encodes a string into bytes using Latin-1 (standard PDF encoding), with a fallback to UTF-8.

    This utility includes a micro-cache (``_B_CACHE``) for short strings (length < 2)
    to optimize repeated encoding of common PDF delimiters like ``(``, ``)``, or ``/``.

    :param s: The input string or bytes.
    :return: The encoded byte string.
    """
    if s in _B_CACHE:
        return _B_CACHE[s]

    if isinstance(s, bytes):
        return s

    try:
        r = s.encode("latin-1")
    except Exception:
        r = s.encode("utf-8")

    if isinstance(s, str) and len(s) < 2:
        _B_CACHE[s] = r

    return r

class IncrementalPdfMerge:
    """
    A utility class to perform an Incremental Update by merging an overlay PDF
    onto an existing PDF document.

    This class handles the low-level PDF structure required to append new content
    (such as a visual signature layer or stamp) to the end of a file without
    altering the original byte range. This approach ensures that the original
    document structure remains intact, which is essential for preserving existing
    digital signatures.

    The implementation follows the **Adobe PDF Reference (v1.7)** specifications
    for Incremental Updates, manually constructing the necessary:

    * **Indirect Objects:** For the new content streams and resources.
    * **Cross-Reference (XRef) Table:** To index the new objects.
    * **Trailer Dictionary:** To link the new update to the previous file version.

    (Ref: ISO 32000-1 / https://ia601001.us.archive.org/1/items/pdf1.7/pdf_reference_1-7.pdf)

    :param pdf_raw: The binary content of the original PDF file.
    :type pdf_raw: bytes
    """

    def __init__(self, pdf_raw: bytes) -> None:
        """
        Initializes the output stream with the original PDF content.

        Creates a BytesIO buffer containing ``pdf_raw`` and moves the cursor
        to the very end of the stream. This prepares the buffer for appending
        the incremental update block (new objects, XRef table, and trailer).

        :param pdf_raw: The raw byte data of the source PDF.
        :type pdf_raw: bytes
        """
        self.pdf_raw = pdf_raw
        self.output_stream = io.BytesIO(self.pdf_raw)
        self.output_stream.seek(0, io.SEEK_END)

    def get_output_stream(self) -> io.BytesIO:
        """
        Retrieves the active file-like object used for writing.

        This stream is positioned at the end of the file (or wherever the last
        write occurred).

        :return: The BytesIO stream containing the PDF data.
        :rtype: io.BytesIO
        """
        return self.output_stream

    def get_output_stream_value(self) -> bytes:
        """
        Retrieves the complete binary content of the PDF.

        This returns the full file data, including the original content plus
        any newly incremented data (objects, XRef, trailer) that has been appended to the
        stream so far.

        :return: The full PDF as a byte string.
        :rtype: bytes
        """
        return self.output_stream.getvalue()

    def merge_pdf(self, overlay_pdf: PdfFileReader) -> None:
        """
        Merges the content of an overlay PDF onto the current PDF output stream.

        This method orchestrates the incremental update process by:
        1. Loading the current PDF state.
        2. Merging page content from the ``overlay_pdf``.
        3. Identifying modified objects.
        4. Writing the incremental update to the output stream.

        :param overlay_pdf: A reader object containing the content to be overlayed.
                            Must have the same number of pages as the current PDF.
        :type overlay_pdf: PdfFileReader
        :return: None
        """
        pdf_reader, incremented_objects = self._merge_pdf_pages(overlay_pdf)
        self._write_incremented_pdf(pdf_reader, incremented_objects)

    def _merge_pdf_pages(self, overlay_pdf: PdfFileReader) -> tuple[PdfFileReader, dict[int, Any]]:
        """
        Internal helper to merge page content while preserving Object IDs.

        This method loads the current byte stream and iterates through pages to apply
        the overlay.

        .. note:: **Non-Destructive Merging**
           This method modifies the existing Page Objects' ``/Annots``, ``/Contents``,
           and ``/Resources`` in place by appending to them. Crucially, it does **not**
           alter the Object ID or invalidate existing indirect references.

           This preserves the integrity of original references (e.g., Object 12),
           ensuring they remain valid for the subsequent incremental update sweep.

        :param overlay_pdf: The source PDF containing the overlay content.
        :type overlay_pdf: PdfFileReader
        :return: A tuple containing:
                 1. The ``PdfFileReader`` instance of the current stream.
                 2. A dictionary mapping Object IDs (int) to the modified Page objects.
        :rtype: tuple[PdfFileReader, dict[int, Any]]
        """
        # 1. Load the current output stream PDF bytes in memory
        pdf_reader = PdfFileReader(io.BytesIO(self.get_output_stream_value()), strict=False)

        # 2. Merge Page Content (Non-Destructive):
        # We use pypdf to overlay the new PDF content onto the existing pages.
        # Crucially, pypdf modifies the existing Page Object's /Annots, /Contents, and
        # /Resources in place (appending to them) without altering its Object ID or
        # invalidating existing indirect references. This preserves the integrity of
        # the original reference (e.g., Object 12), ensuring it remains valid for
        # the subsequent incremental update sweep.
        incremented_objects = {}
        for page_index in range(0, len(pdf_reader.pages)):
            page = pdf_reader.pages[page_index]
            self._merge_page(page, overlay_pdf.pages[page_index])
            incremented_objects[page.indirect_reference.idnum] = page
            # Invalidate cache and cache new page reference so it would be seen while sweeping indirect references later on
            pdf_reader.cache_indirect_object(page.indirect_reference.generation, page.indirect_reference.idnum, page)

        return pdf_reader, incremented_objects

    def _merge_page(
        self,
        page1,
        page2,
        page2transformation = None,
        ctm = None,
        expand: bool = False,
    ) -> None:
        """
        Merges the content, resources, and annotations of a source page into a target page.

        This method modifies ``page1`` in-place. It performs three critical operations:

        1.  **Resource Merging:** Combines resource dictionaries (Fonts, XObjects, ExtGState).
            Conflicting symbols are renamed in ``page2`` to prevent collisions.
        2.  **Annotation Merging:** Appends annotations from the source page to the target.
        3.  **Content Stream Assembly:** The content of ``page2`` is appended to ``page1``.

        .. note:: **Content Isolation & Clipping**
           To ensure visual integrity:

           * The content of ``page2`` is clipped to its trimbox before merging.
           * Both original and new content streams are isolated using push/pop graphics state
               operators (`q`/`Q`) to prevent state leakage (e.g., color settings) between pages.

        :param page1: The target page object to be modified.
        :type page1: PageObject
        :param page2: The source page object to overlay onto the target.
        :type page2: PageObject
        :param page2transformation: An optional callable to transform the content stream
                                    of ``page2`` before merging (e.g., rotation or scaling).
        :type page2transformation: Optional[Callable[[Any], ContentStream]] or None
        :param ctm: The Current Transformation Matrix used if expanding the page boundaries.
        :type ctm: Optional[CompressedTransformationMatrix] or None
        :param expand: If True, expands the media box of ``page1`` to accommodate ``page2``
                       (requires ``ctm``). Defaults to False.
        :type expand: bool
        :return: None
        """
        # First we work on merging the resource dictionaries.  This allows us
        # to find out what symbols in the content streams we might need to
        # rename.

        new_resources = DictionaryObject()
        rename = {}
        try:
            original_resources = cast(DictionaryObject, page1[PG.RESOURCES].get_object())
        except KeyError:
            original_resources = DictionaryObject()
        try:
            page2resources = cast(DictionaryObject, page2[PG.RESOURCES].get_object())
        except KeyError:
            page2resources = DictionaryObject()
        new_annots = ArrayObject()

        for page in (page1, page2):
            if PG.ANNOTS in page:
                annots = page[PG.ANNOTS]
                if isinstance(annots, ArrayObject):
                    for ref in annots:
                        new_annots.append(ref)

        for res in (
            RES.EXT_G_STATE,
            RES.FONT,
            RES.XOBJECT,
            RES.COLOR_SPACE,
            RES.PATTERN,
            RES.SHADING,
            RES.PROPERTIES,
        ):
            new, newrename = self._merge_resources(
                original_resources, page2resources, res
            )
            if new:
                new_resources[NameObject(res)] = new
                rename.update(newrename)

        # Combine /ProcSet sets.
        new_resources[NameObject(RES.PROC_SET)] = ArrayObject(
            frozenset(
                original_resources.get(RES.PROC_SET, ArrayObject()).get_object()
            ).union(
                frozenset(page2resources.get(RES.PROC_SET, ArrayObject()).get_object())
            )
        )

        new_content_array = ArrayObject()

        original_content = page1.get_contents()
        if original_content is not None:
            new_content_array.append(
                self._push_pop_gs(original_content, page1.pdf)
            )

        page2content = page2.get_contents()
        if page2content is not None:
            page2content = ContentStream(page2content, page1.pdf)
            rect = page2.trimbox
            page2content.operations.insert(
                0,
                (
                    map(
                        FloatObject,
                        [
                            rect.left,
                            rect.bottom,
                            rect.width,
                            rect.height,
                        ],
                    ),
                    "re",
                ),
            )
            page2content.operations.insert(1, ([], "W"))
            page2content.operations.insert(2, ([], "n"))
            if page2transformation is not None:
                page2content = page2transformation(page2content)
            page2content = self._content_stream_rename(
                page2content, rename, page1.pdf
            )
            page2content = self._push_pop_gs(page2content, page1.pdf)
            new_content_array.append(page2content)

        # if expanding the page to fit a new page, calculate the new media box size
        if expand:
            self._expand_mediabox(page1, page2, ctm)

        page1[NameObject(PG.CONTENTS)] = ContentStream(new_content_array, page1.pdf)
        page1[NameObject(PG.RESOURCES)] = new_resources
        page1[NameObject(PG.ANNOTS)] = new_annots

    def _merge_resources(
        self, res1: DictionaryObject, res2: DictionaryObject, resource: Any
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Merges a specific resource category from two dictionaries, handling name collisions.

        This method extracts a specific resource type (e.g., ``/Font``, ``/XObject``) from
        both dictionaries and combines them.

        **Collision Handling:**
        If a resource key from ``res2`` matches a key in ``res1`` but points to a
        different object, the resource from ``res2`` is renamed using a UUID suffix.
        If the keys point to the exact same object, no renaming occurs.

        :param res1: The resource dictionary of the target page (base).
        :type res1: DictionaryObject
        :param res2: The resource dictionary of the overlay page (source).
        :type res2: DictionaryObject
        :param resource: The specific resource key to merge (e.g., ``/Font``, ``/ExtGState``).
        :type resource: Any
        :return: A tuple containing:

                 1. **Merged Dictionary:** A new ``DictionaryObject`` containing the union of resources.
                 2. **Rename Map:** A dictionary ``{old_name: new_name}`` mapping original keys
                    from ``res2`` to their new unique names.
        :rtype: tuple[dict, dict]
        """
        new_res = DictionaryObject()
        new_res.update(res1.get(resource, DictionaryObject()).get_object())
        page2res = cast(
            DictionaryObject, res2.get(resource, DictionaryObject()).get_object()
        )
        rename_res = {}
        for key in list(page2res.keys()):
            if key in new_res and new_res.raw_get(key) != page2res.raw_get(key):
                newname = NameObject(key + str(uuid.uuid4()))
                rename_res[key] = newname
                new_res[newname] = page2res.raw_get(key)
            elif key not in new_res:
                new_res[key] = page2res.raw_get(key)
        return new_res, rename_res

    def _content_stream_rename(
        self, stream: ContentStream, rename: Dict[Any, Any], pdf: Any  # PdfReader
    ) -> ContentStream:
        """
        Updates resource references in a content stream to match merged resources.

        This method iterates through all PDF operators in the provided ``stream``.
        It inspects the operands (arguments) of each operator; if an operand is a
        ``NameObject`` (e.g., ``/F1``) that appears in the ``rename`` map, it is
        replaced with the new unique name (e.g., ``/F1uuid...``).

        This ensures that the content stream correctly points to the renamed resources
        generated during the resource merge process.

        :param stream: The content stream containing PDF operators to process.
        :type stream: ContentStream
        :param rename: A mapping of ``{old_name: new_name}`` generated by :meth:`_merge_resources`.
                       If empty, the stream is returned unchanged.
        :type rename: dict
        :param pdf: The associated PDF object (required to instantiate the new ContentStream).
        :type pdf: PdfReader or Any
        :return: The processed content stream with updated resource names.
        :rtype: ContentStream
        :raises KeyError: If the operands of an operator are not of type ``list`` or ``dict``.
        """
        if not rename:
            return stream
        stream = ContentStream(stream, pdf)
        for operands, _operator in stream.operations:
            if isinstance(operands, list):
                for i in range(len(operands)):
                    op = operands[i]
                    if isinstance(op, NameObject):
                        operands[i] = rename.get(op, op)
            elif isinstance(operands, dict):
                for i in operands:
                    op = operands[i]
                    if isinstance(op, NameObject):
                        operands[i] = rename.get(op, op)
            else:
                raise KeyError(f"type of operands is {type(operands)}")
        return stream

    def _push_pop_gs(self, contents: Any, pdf: Any) -> ContentStream:
        """
        Wraps a content stream in Graphics State operators to isolate its state.

        This method prepends the ``q`` (Save Graphics State) operator and appends the
        ``Q`` (Restore Graphics State) operator to the provided content stream.

        **Purpose:**
        This ensures that any state changes (like Color Space, CTM transformations,
        or Line Widths) made within this content stream do not leak out and affect
        subsequent content or pages. It effectively creates a sandbox for the content.

        :param contents: The source content to wrap (can be a raw stream or ContentStream).
        :type contents: ContentStream or Any
        :param pdf: The associated PDF object required to build the new ContentStream.
        :type pdf: PdfReader or Any
        :return: A new ContentStream containing the original operations sandwiched between ``q`` and ``Q``.
        :rtype: ContentStream
        """
        stream = ContentStream(contents, pdf)
        stream.operations.insert(0, ([], "q"))
        stream.operations.append(([], "Q"))
        return stream

    def _expand_mediabox(
        self, page1, page2, ctm
    ) -> None:
        """
        Expands the boundaries (MediaBox) of the target page to encompass the overlay page.

        This method calculates the union of ``page1``'s existing MediaBox and the
        transformed bounding box of ``page2``. It ensures that if ``page2`` is larger
        or shifted outside the original view (via ``ctm``), the canvas size of ``page1``
        is increased so no content is clipped.

        **Transformation Logic:**
        If a CTM (Current Transformation Matrix) is provided, it is applied to the
        four corners of ``page2`` before calculating the new boundary extrema.
        The transformation follows standard affine mapping:

        .. math::
            x' = a \cdot x + c \cdot y + e \\
            y' = b \cdot x + d \cdot y + f

        :param page1: The target page whose MediaBox will be updated in place.
        :type page1: PageObject
        :param page2: The source page determining the expansion requirements.
        :type page2: PageObject
        :param ctm: A 6-element list ``[a, b, c, d, e, f]`` representing the transformation
                    matrix. If None, identity transformation is assumed.
        :type ctm: list[float] or None
        :return: None
        """
        corners1 = (
            page1.mediabox.left.as_numeric(),
            page1.mediabox.bottom.as_numeric(),
            page1.mediabox.right.as_numeric(),
            page1.mediabox.top.as_numeric(),
        )
        corners2 = (
            page2.mediabox.left.as_numeric(),
            page2.mediabox.bottom.as_numeric(),
            page2.mediabox.left.as_numeric(),
            page2.mediabox.top.as_numeric(),
            page2.mediabox.right.as_numeric(),
            page2.mediabox.top.as_numeric(),
            page2.mediabox.right.as_numeric(),
            page2.mediabox.bottom.as_numeric(),
        )
        if ctm is not None:
            ctm = tuple(float(x) for x in ctm)  # type: ignore[assignment]
            new_x = tuple(
                ctm[0] * corners2[i] + ctm[2] * corners2[i + 1] + ctm[4]
                for i in range(0, 8, 2)
            )
            new_y = tuple(
                ctm[1] * corners2[i] + ctm[3] * corners2[i + 1] + ctm[5]
                for i in range(0, 8, 2)
            )
        else:
            new_x = corners2[0:8:2]
            new_y = corners2[1:8:2]
        lowerleft = (min(new_x), min(new_y))
        upperright = (max(new_x), max(new_y))
        lowerleft = (min(corners1[0], lowerleft[0]), min(corners1[1], lowerleft[1]))
        upperright = (
            max(corners1[2], upperright[0]),
            max(corners1[3], upperright[1]),
        )

        page1.mediabox.lower_left = lowerleft
        page1.mediabox.upper_right = upperright

    def _write_incremented_pdf(self, pdf_reader, incremented_objects):
        """
        Finalizes the incremental update by writing modified objects and the trailer.

        This method orchestrates the low-level writing process. It appends the
        incremental update section to the end of the existing file, ensuring validity
        without rewriting the entire PDF.

        **Execution Flow:**

        1.  **ID Resolution:** Determines the next available Object ID (`start_id`).
            It attempts to read the trailer ``/Size``; if missing (common in PDF 1.5+
            Object Streams), it calculates the max ID by scanning existing XRefs.
        2.  **Graph Traversal:** Recursively sweeps from the Catalog (`/Root`) to detect
            any *newly created* objects injected during the merge that weren't explicitly
            tracked. These are assigned valid IDs and added to the write queue.
        3.  **Object Writing:** Serializes all modified and new objects to the output stream.
        4.  **XRef & Trailer:** Generates the new Cross-Reference Table and Trailer dictionary,
            linking back to the ``original_startxref``.

        :param pdf_reader: The reader instance representing the current PDF state.
        :type pdf_reader: PdfFileReader
        :param incremented_objects: A dictionary mapping Object IDs to the Page objects
                                    that were explicitly modified during the merge.
        :type incremented_objects: dict[int, Any]
        :return: None
        """
        # 1. Trust the trailer first (Standard behavior)
        size = pdf_reader.trailer.get(TK.SIZE)

        # 2. If missing, calculate safely (Fall back for PDF 1.5+)
        if size is None:
            # Gather IDs, defaulting to {0} to prevent max() crash on empty files
            all_ids = set(pdf_reader.xref_objStm.keys()) | {0}
            for gen in pdf_reader.xref.values():
                all_ids.update(gen.keys())
            size = max(all_ids) + 1
        start_id = size
        original_startxref = self._find_last_startxref(self.get_output_stream_value())

        # 3. We perform a recursive traversal starting from the Catalog (/Root) to
        # detect any newly created objects injected during the merge. These objects
        # are assigned valid, contiguous Object IDs to ensure they are correctly
        # indexed in the upcoming incremental XRef update. Additionally, this step
        # resolves circular references (e.g., objects pointing back to their parent
        # Pages), ensuring the integrity of the object graph.
        catalog = cast(DictionaryObject, pdf_reader.trailer[TK.ROOT])
        new_objects = self._sweep_indirect_references(pdf_reader, catalog, start_id)
        for key, val in new_objects.items():
            incremented_objects[key] = val

        # 4. Write all objects to the output stream
        new_xref_entries = self._write_objects(incremented_objects)

        # 5. Generate Xref table
        xref_start, new_size = self._write_xref_table(new_xref_entries)

        # 6. Construct the PDF trailer
        self._write_trailer(pdf_reader, original_startxref, xref_start, new_size)

    def _write_objects(self, incremented_objects):
        """
        Serializes a collection of PDF objects to the output stream.

        This method iterates through the provided objects, writes them to the
        stream in the standard PDF object format (``ID 0 obj ... endobj``),
        and records the file pointer position (byte offset) for each object.

        :param incremented_objects: A dictionary mapping Object IDs (int) to the
                                    PDF objects (e.g., PageObject, DictionaryObject).
        :type incremented_objects: dict[int, Any]
        :return: A dictionary mapping Object IDs to their new byte offsets in the stream.
                 This is used to construct the XRef table.
        :rtype: dict[int, int]
        """
        output = self.output_stream
        new_xref_entries = {}
        for obj_id, obj_data in sorted(incremented_objects.items()):
            new_xref_entries[obj_id] = output.tell()
            output.write(b_(str(obj_id)) + b" 0 obj\n")
            obj_data.write_to_stream(output, None)
            output.write(b"\nendobj\n")

        return new_xref_entries

    def _write_xref_table(self, new_xref_entries):
        """
        Writes the Cross-Reference (XRef) table to the output stream.

        This method formats the table according to ISO 32000-1, creating subsections
        as needed for the provided object entries.

        :param new_xref_entries: A dictionary mapping Object IDs to their byte offsets.
        :return: A tuple containing the byte offset of the 'xref' keyword and the
                 calculated size of the PDF (max_id + 1).
        :rtype: tuple[int, int]
        """
        output = self.output_stream

        # ----------------------------------------------------------------------
        # XRef CONSTRUCTIONS (ISO 32000-1, Section 7.5.4)
        # ----------------------------------------------------------------------
        # The PDF specification allows the cross-reference table to be split
        # into multiple subsections to support "sparse" Object ID ranges.
        #
        # This block identifies clusters of contiguous Object IDs (e.g., the
        # modified Page Object at ID 12, followed by a gap, then new Objects
        # 50-55) and writes a separate subsection header for each cluster.
        # ----------------------------------------------------------------------
        xref_start = output.tell()
        output.write(b"xref\n")

        # Object 0 (Sentinel Entry):
        # The mandatory first entry of the XRef table. It acts as the head of the
        # linked list for deleted (free) objects.
        # - Offset 0000000000: Points to the next free object index (0 if none).
        # - Generation 65535: Max integer ensures Object 0 is never reused/allocated.
        # - Type 'f': Marks this entry as 'Free'.
        if 0 not in new_xref_entries:
            new_xref_entries[0] = 0

        sorted_ids = sorted(new_xref_entries.keys())
        i = 0
        while i < len(sorted_ids):
            start_j = i
            while i + 1 < len(sorted_ids) and sorted_ids[i + 1] == sorted_ids[i] + 1:
                i += 1

            chunk_ids = sorted_ids[start_j: i + 1]
            output.write(b_(f"{chunk_ids[0]} {len(chunk_ids)}\n"))
            for oid in chunk_ids:
                if oid == 0:
                    output.write(b_(f"{0:0>10} {65535:0>5} f \n"))
                else:
                    offset = new_xref_entries[oid]
                    output.write(b_(f"{offset:0>10} {0:0>5} n \n"))

            i += 1

        return xref_start, max(sorted_ids) + 1

    def _write_trailer(self, pdf_reader, original_startxref, xref_start, size):
        """
        Writes the trailer dictionary and the final end-of-file markers.

        This method constructs a new trailer that links the incremental update
        back to the original document (via the ``/Prev`` key) and writes the
        ``startxref`` offset and ``%%EOF`` marker.

        :param pdf_reader: The reader instance, used to copy original Root, Info, and ID.
        :param original_startxref: The byte offset of the previous XRef table (for the ``/Prev`` chain).
        :param xref_start: The byte offset of the newly written XRef table.
        :param size: The total number of objects in the updated PDF.
        :return: None
        """
        output = self.output_stream

        # ----------------------------------------------------------------------
        # TRAILER CONSTRUCTION (ISO 32000-1, Section 7.5.5)
        # ----------------------------------------------------------------------
        # The trailer dictionary allows the PDF reader to quickly locate key
        # document structures. For an Incremental Update, it must:
        # 1. Point to the Catalog (/Root) and Metadata (/Info) of the original file.
        # 2. Define the total number of objects (/Size) including the new additions.
        # 3. Chain back to the previous XRef table via the /Prev key, preserving
        #    the document's revision history.
        # 4. Replicate critical security identifiers (/ID and /Encrypt) to maintain
        #    file integrity and access permissions.
        # ----------------------------------------------------------------------
        output.write(b"trailer\n")
        trailer = DictionaryObject()
        trailer.update(
            {
                NameObject(TK.SIZE): NumberObject(size),
                NameObject(TK.ROOT): pdf_reader.trailer.raw_get(TK.ROOT),
                NameObject(TK.INFO): pdf_reader.trailer[TK.INFO],
                NameObject(TK.PREV): NumberObject(original_startxref)
            }
        )
        if hasattr(pdf_reader, "_ID"):
            trailer[NameObject(TK.ID)] = pdf_reader._ID
        if hasattr(pdf_reader, "_encrypt"):
            trailer[NameObject(TK.ENCRYPT)] = pdf_reader._encrypt
        trailer.write_to_stream(output, None)
        output.write(b_(f"\nstartxref\n{xref_start}\n%%EOF\n"))  # EOF

    def _find_last_startxref(self, data):
        """
        Locates the byte offset of the most recent Cross-Reference (XRef) table.

        According to **ISO 32000-1**, a PDF reader must read the file from the end
        to find the ``startxref`` keyword. This keyword points to the location
        of the last valid XRef table (or XRef stream), which serves as the entry
        point for parsing the document's structure.

        This method scans backwards from the end of the data to find the last
        occurrence of ``startxref`` and parses the integer offset following it.

        **Example:**

        .. code-block:: python

            data = b'... trailer << /Size 15 ... >> \\n startxref \\n 12345 \\n %%EOF'
            offset = self._find_last_startxref(data)
            # Returns: 12345

        :param data: The raw binary data of the PDF file.
        :type data: bytes
        :return: The byte offset of the last XRef table, or 0 if the keyword is not found.
        :rtype: int
        """
        # Search from end of file for startxref
        idx = data.rfind(b"startxref")
        if idx == -1: return 0
        return int(data[idx:].splitlines()[1].strip())

    def _sweep_indirect_references(self, pdf_reader: PdfFileReader, root, next_id) -> dict[int, Any]:
        """
        Recursively traverses the PDF object graph to identify new objects and update
        references.

        This method performs a **Depth-First Search (DFS)** starting from the provided
        ``root`` object. Its primary goals are:

        1.  **Discovery:** Identify all reachable objects (dictionaries, arrays, streams).
        2.  **Resolution:** Differentiate between existing objects (from the original PDF)
            and new objects (from the overlay).
        3.  **Remapping:** Assign valid Object IDs to new objects using ``_resolve_indirect_object``.
        4.  **Pointer Fixup:** If a child object is remapped to a new ID, this method updates
            the parent container (Dictionary or Array) to point to the new reference.

        It uses an iterative stack-based approach (instead of recursion) to prevent
        stack overflow errors on deeply nested PDFs.

        :param pdf_reader: The reader instance for the original source PDF.
        :type pdf_reader: PdfFileReader
        :param root: The starting point of the traversal (usually the Document Catalog).
        :type root: DictionaryObject or ArrayObject
        :param next_id: The first available Object ID to use for new objects.
        :type next_id: int
        :return: None
        """
        incremented_objects = {}
        writer = PdfFileWriter()  # A temporary PdfFileWriter used to wrap new objects

        idnum_hash = {}
        stack = deque()
        discovered = []
        parent = None
        grant_parents = []
        key_or_id = None

        # Start from root
        stack.append((root, parent, key_or_id, grant_parents))

        while len(stack):
            data, parent, key_or_id, grant_parents = stack.pop()

            # Build stack for a processing depth-first
            if isinstance(data, DictionaryObject):
                for key, value in list(data.items()):
                    stack.append(
                        (
                            value,
                            data,
                            key,
                            grant_parents + [parent] if parent is not None else [],
                        )
                    )
            elif isinstance(data, ArrayObject):
                for idx in range(len(data)):
                    value = data[idx]
                    stack.append(
                        (
                            value,
                            data,
                            idx,
                            grant_parents + [parent] if parent is not None else [],
                        )
                    )
            elif isinstance(data, IndirectObject):
                data, next_id = self._resolve_indirect_object(pdf_reader, writer, data, idnum_hash, incremented_objects, next_id)

                if str(data) not in discovered:
                    discovered.append(str(data))
                    stack.append((data.get_object(), None, None, []))

            # Check if data has a parent and if it is a dict or an array update the value
            if isinstance(parent, (DictionaryObject, ArrayObject)):
                if isinstance(data, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    incremented_objects[next_id] = data
                    data_hash = data.hash_value()
                    idnum_hash[data_hash] = IndirectObject(next_id, 0, writer)
                    self._pdf_writer_append_obj(writer, data, next_id)
                    next_id += 1
                    data = idnum_hash[data_hash]

                update_hashes = []

                # Data changed and thus the hash value changed
                old_data = parent[key_or_id] if isinstance(parent, ArrayObject) else parent.raw_get(key_or_id)
                if old_data != data:
                    update_hashes = [parent.hash_value()] + [
                        grant_parent.hash_value() for grant_parent in grant_parents
                    ]
                    parent[key_or_id] = data

                # Update old hash value to new hash value
                for old_hash in update_hashes:
                    indirect_reference = idnum_hash.pop(old_hash, None)

                    if indirect_reference is not None:
                        indirect_reference_obj = indirect_reference.get_object()

                        if indirect_reference_obj is not None:
                            idnum_hash[
                                indirect_reference_obj.hash_value()
                            ] = indirect_reference

        return incremented_objects

    def _resolve_indirect_object(
            self,
            pdf_reader: PdfFileReader,
            writer: PdfFileWriter,
            data: IndirectObject,
            idnum_hash: dict[bytes, Any],
            incremented_objects: dict[int, Any],
            next_id: int
    ) -> IndirectObject:
        """
        Resolves an indirect reference to its concrete object and determines its final Object ID.

        This method acts as a router/deduplicator:

        * **Existing Objects:** If the object belongs to ``pdf_reader`` (the original file),
            it preserves the original Object ID.
        * **New Objects:** If the object is foreign (from the overlay PDF), it assigns a
            new, unique Object ID (``next_id``), registers it in ``incremented_objects``,
            and increments the counter.
        * **Deduplication:** Uses ``idnum_hash`` to ensure that identical objects are
            reused rather than duplicated in the output file.

        :param data: The indirect reference to resolve.
        :type data: IndirectObject
        :param pdf_reader: The reader for the original PDF.
        :param writer: A temporary PdfFileWriter used to wrap new objects.
        :param idnum_hash: A cache dictionary mapping object hashes to their resolved IndirectObjects.
        :param incremented_objects: The registry of new objects for the incremental update.
        :param next_id: The next available Object ID.
        :return: A tuple containing the resolved ``IndirectObject`` and the (possibly incremented) ``next_id``.
        :rtype: tuple[IndirectObject, int]
        :raises ValueError: If the underlying PDF stream is closed.
        """
        if hasattr(data.pdf, "stream") and data.pdf.stream.closed:
            raise ValueError(f"I/O operation on closed file: {data.pdf.stream.name}")

        # Get real object from the indirect object
        real_obj = data.pdf.get_object(data)

        if real_obj is None:
            _logger.warning(
                f"Unable to resolve [{data.__class__.__name__}: {data}], "
                "returning NullObject instead",
                __name__,
            )
            real_obj = NullObject()

        hash_value = real_obj.hash_value()

        # Check if object is handled
        if hash_value in idnum_hash:
            return idnum_hash[hash_value], next_id

        if data.pdf == pdf_reader:
            idnum_hash[hash_value] = IndirectObject(data.idnum, 0, pdf_reader)
        # This is new incremented object in this pdf
        else:
            incremented_objects[next_id] = real_obj
            idnum_hash[hash_value] = IndirectObject(next_id, 0, writer)
            self._pdf_writer_append_obj(writer, real_obj, next_id)
            next_id += 1

        return idnum_hash[hash_value], next_id

    def _pdf_writer_append_obj(self, writer, obj, obj_id) -> None:
        """
        Internal helper to register an object at a specific ID index within the writer.

        Since PDF Object IDs are 1-based indices, this method ensures the writer's
        internal list is large enough to hold ``obj_id``. It pads the list with
        ``NullObject``s if necessary to fill gaps before placing the target object.

        :param writer: The PdfFileWriter instance (used as a container).
        :param obj: The concrete object to store.
        :param obj_id: The target Object ID (integer).
        :return: None
        """
        while len(writer._objects) < obj_id:
            writer._objects.append(NullObject())
        writer._objects[obj_id - 1] = obj
