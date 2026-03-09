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
import struct
import datetime
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
    BooleanObject,
    NumberObject,
    FloatObject,
    TextStringObject,
    ContentStream,
    DecodedStreamObject as StreamObject,
)

from .constants import TrailerKeys as TK, Resources as RES, PageAttributes as PG

_logger = logging.getLogger(__name__)

def b_(s: str | bytes) -> bytes:
    """
    Converts a string or bytes object into raw bytes.

    If the input is already a bytes object, it is returned unchanged.
    Strings are encoded using Latin-1 (the standard encoding for basic PDF
    structures and operators), with a fallback to UTF-8 if the string
    contains characters outside the Latin-1 range.

    :param s: The input string or bytes to encode.
    :return: The resulting encoded byte string.
    """

    if isinstance(s, bytes):
        return s

    try:
        r = s.encode("latin-1")
    except Exception:
        r = s.encode("utf-8")

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

    (Ref: Adobe PDF Reference (v1.7) / https://ia601001.us.archive.org/1/items/pdf1.7/pdf_reference_1-7.pdf)

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

    def merge_pdf(self, overlay_pdf: PdfFileReader, overlay_pages: set[int] = None, merge_res_as_annotation=False) -> None:
        """
        Merges the content of an overlay PDF onto the current PDF output stream.

        This method orchestrates an incremental update (Adobe PDF Reference, Sixth Edition,
        version 1.7 (2006), Section 3.4.5) to apply the overlay without rewriting the
        entire original file. The process involves:

        1. Loading the current PDF state from the active output stream.
        2. Merging the visual page content from the ``overlay_pdf`` onto the existing pages.
        3. Identifying all newly created or modified objects (e.g., updated page dictionaries).
        4. Writing the new objects and the updated XRef stream to the end of the file.

        :param overlay_pdf: A reader object containing the content to be overlaid.
            It must contain the same number of pages as the current PDF.
        :type overlay_pdf: PdfFileReader
        :param overlay_pages: Optional set of PDF page indices indicating which
            pages should receive the overlay.
        :type overlay_pages: set[int] or None
        :param merge_res_as_annotation: If ``True``, merges the overlay resources
            as a PDF annotation rather than directly modifying the base page's
            content stream. This is particularly useful for watermarks, signatures,
            or ensuring the overlay remains logically distinct from the base content.
        :type merge_res_as_annotation: bool
        :return: None
        """
        if merge_res_as_annotation:
            pdf_reader, incremented_objects = self._merge_pdf_pages_as_annotation(overlay_pdf, overlay_pages)
        else:
            pdf_reader, incremented_objects = self._merge_pdf_pages(overlay_pdf, overlay_pages)

        self._write_incremented_pdf(pdf_reader, incremented_objects)

    def _merge_pdf_pages_as_annotation(
            self,
            overlay_pdf: PdfFileReader,
            overlay_pages: set[int] = None,
            annotations_title="overlay"
    ) -> tuple[PdfFileReader, dict[tuple[int, int], Any]]:
        """
        Merges an overlay PDF onto the current PDF by embedding the overlay content
        as a locked Stamp Annotation.

        Instead of destructively merging the overlay directly into the base page's
        ``/Contents`` stream, this method uses a non-destructive approach
        (Adobe PDF Reference 1.7 (2006), Section 8.4). It encapsulates the overlay
        graphics into a discrete, locked layer. The structural process is as follows:

        1. Form XObject Creation (Section 4.9): Extracts the raw content stream and
           resources from the overlay page and wraps them in a Form XObject.
        2. Appearance Stream (Section 8.4.4): Assigns the Form XObject to the
           normal appearance state (``/AP << /N ... >>``) of a new annotation.
        3. Stamp Annotation (Section 8.4.5): Creates a ``/Stamp`` annotation
           dictionary locked via ``/F 196`` (Print, NoZoom, NoRotate, ReadOnly),
           ``/Locked``, and ``/LockedContents`` flags. It also injects essential
           tracking metadata (``/NM`` UUID, ``/M`` modification date).
        4. Page Attachment: Appends the annotation reference to the base page's
           ``/Annots`` array and flags the modified page (or ``/Annots`` array itself)
           for the incremental update writer.

        :param overlay_pdf: A reader object containing the visual content to be stamped.
            It must contain the same number of pages as the current PDF.
        :type overlay_pdf: PdfFileReader
        :param overlay_pages: Optional set of PDF page indices indicating which
            pages should receive the overlay.
        :type overlay_pages: set[int] or None
        :param annotations_title: The text title (``/T``) assigned to the stamp
            annotation, useful for identifying the overlay layer in PDF viewer UI.
            Defaults to "overlay".
        :type annotations_title: str
        :return: A tuple containing the updated state:
            - The ``PdfFileReader`` instance representing the base document.
            - A dictionary of ``incremented_objects`` mapping ``(object_id, generation)``
              tuples to the modified PDF objects.
        :rtype: tuple[PdfFileReader, dict[tuple[int, int], Any]]
        """
        pdf_reader = PdfFileReader(io.BytesIO(self.get_output_stream_value()), strict=False)
        writer = PdfFileWriter()  #A temporary PdfFileWriter used to wrap new objects not to write them
        incremented_objects = {}

        for page_index in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_index]
            if overlay_pages and page_index not in overlay_pages:
                # Still include skipped pages in the incremental update unchanged.
                # This ensures their XRef entries are "owned" by this update,
                # preventing subsequent signings from overriding objects sealed
                # by this signature's ByteRange.
                page_ref_id = page.indirect_reference.idnum
                page_ref_gen = page.indirect_reference.generation
                if (page_ref_id, page_ref_gen) not in incremented_objects:
                    incremented_objects[(page_ref_id, page_ref_gen)] = page
                continue
            overlay_page = overlay_pdf.pages[page_index]

            content_stream = overlay_page.get_contents()
            if not content_stream:
                continue  # Skip if the ReportLab page is completely blank

            overlay_resources = overlay_page.get(PG.RESOURCES, DictionaryObject())
            media_box = page.mediabox

            # Create the Appearance Stream (The ReportLab Graphics)
            appearance_stream = StreamObject()
            appearance_stream._data = content_stream.get_data()
            appearance_stream.update({
                NameObject("/Type"): NameObject("/XObject"),
                NameObject("/Subtype"): NameObject("/Form"),
                NameObject("/FormType"): NumberObject(1),
                NameObject("/BBox"): ArrayObject([
                    NumberObject(media_box.left), NumberObject(media_box.bottom),
                    NumberObject(media_box.right), NumberObject(media_box.top)
                ]),
                NameObject("/Resources"): overlay_resources
            })

            # Create the Annotation
            appearance_stream_ref = writer._add_object(appearance_stream)
            annot_dict = DictionaryObject()
            annot_dict.update({
                NameObject("/Type"): NameObject("/Annot"),
                NameObject("/Subtype"): NameObject("/Stamp"),
                NameObject("/T"): TextStringObject(f"{annotations_title}_page_{page_index}"),
                NameObject("/Rect"): ArrayObject([
                    NumberObject(media_box.left), NumberObject(media_box.bottom),
                    NumberObject(media_box.right), NumberObject(media_box.top)
                ]),
                NameObject("/F"): NumberObject(196),
                NameObject("/Locked"): BooleanObject(True),
                NameObject("/LockedContents"): BooleanObject(True),
                NameObject("/AP"): DictionaryObject({
                    NameObject("/N"): appearance_stream_ref
                }),
                NameObject("/P"): page.indirect_reference,  # Anchor to the specific exact page reference
                NameObject("/NM"): TextStringObject(str(uuid.uuid4())), # Unique UUID name to prevent orphaned detached states
                NameObject("/M"): TextStringObject(datetime.datetime.now(datetime.timezone.utc).strftime("D:%Y%m%d%H%M%SZ"))
            })

            # Attach the Annotation to the Original Page
            annot_ref = writer._add_object(annot_dict)
            try:
                raw_annots = page.raw_get(PG.ANNOTS)
            except KeyError:
                raw_annots = None
            if raw_annots and isinstance(raw_annots, IndirectObject):
                annots_array = raw_annots.get_object()
                annots_array.append(annot_ref)
                raw_id = raw_annots.idnum
                raw_gen = raw_annots.generation
                if (raw_id, raw_gen) not in incremented_objects:
                    incremented_objects[(raw_id, raw_gen)] = annots_array
                pdf_reader.cache_indirect_object(raw_gen, raw_id, annots_array)
            else:
                if raw_annots is None:
                    raw_annots = ArrayObject()

                raw_annots.append(annot_ref)
                page[NameObject(PG.ANNOTS)] = raw_annots

                page_ref_id = page.indirect_reference.idnum
                page_ref_gen = page.indirect_reference.generation
                incremented_objects[(page_ref_id, page_ref_gen)] = page
                pdf_reader.cache_indirect_object(page_ref_gen, page_ref_id, page)

        return pdf_reader, incremented_objects

    def _merge_pdf_pages(self, overlay_pdf: PdfFileReader, overlay_pages: set[int] = None) -> tuple[PdfFileReader, dict[int, Any]]:
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
        :param overlay_pages: Optional set of PDF page indices indicating which
            pages should receive the overlay.
        :type overlay_pages: set[int] or None
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
            if overlay_pages and page_index not in overlay_pages:
                continue

            page = pdf_reader.pages[page_index]
            self._merge_page(page, overlay_pdf.pages[page_index])
            page_ref_id = page.indirect_reference.idnum
            page_ref_gen = page.indirect_reference.generation
            incremented_objects[(page_ref_id, page_ref_gen)] = page
            # Invalidate cache and cache new page reference so it would be seen while sweeping indirect references later on
            pdf_reader.cache_indirect_object(page_ref_gen, page_ref_id, page)

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
        :raises TypeError: If the operands of an operator are not of type ``list`` or ``dict``.
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
                raise TypeError(f"type of operands is {type(operands)}")
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
        :type incremented_objects: dict[tuple[int, int], Any]
        :return: None
        """
        if incremented_objects is None or len(incremented_objects) == 0:
            return

        # Get xref start offset
        original_startxref = self._find_last_startxref(self.get_output_stream_value())

        # Check if the original PDF uses an XRef stream
        # PyPDF strips /Type /XRef from the trailer dict.
        # Check the raw bytes at original_startxref: if it does not start with 'xref',
        # it is an object representing an XRef stream
        is_xref_stream = pdf_reader.trailer.get(TK.TYPE) == "/XRef"
        if not is_xref_stream:
            raw_data = self.get_output_stream_value()
            target_bytes = raw_data[original_startxref:original_startxref + 20].lstrip()
            if target_bytes and not target_bytes.startswith(b"xref"):
                is_xref_stream = True

        # Trust that the trailer contain a size first (Standard behavior)
        size = pdf_reader.trailer.get(TK.SIZE)

        # If size is missing, it's a xref stream PDF, we need calculate size (Fall back for PDF 1.5+)
        if not size:
            # Gather IDs, defaulting to {0} to prevent max() crash on empty files
            all_ids = set(pdf_reader.xref_objStm.keys()) | {0}
            for gen in pdf_reader.xref.values():
                all_ids.update(gen.keys())
            size = max(all_ids) + 1

        # We perform a recursive traversal starting from the Catalog (/Root) to
        # detect any newly created objects injected during the merge. These objects
        # are assigned valid, contiguous Object IDs to ensure they are correctly
        # indexed in the upcoming incremental XRef update. Additionally, this step
        # resolves circular references (e.g., objects pointing back to their parent
        # Pages), ensuring the integrity of the object graph.
        catalog = cast(DictionaryObject, pdf_reader.trailer[TK.ROOT])
        new_objects = self._sweep_indirect_references(pdf_reader, catalog, size)
        for key, val in new_objects.items():
            incremented_objects[key] = val

        # Write all objects to the output stream
        new_xref_entries = self._write_objects(incremented_objects)

        # construct the end of the PDF
        if is_xref_stream:
            self._write_xref_stream(pdf_reader, new_xref_entries, original_startxref, size)
        else:
            # Generate Xref table
            xref_start, max_entry_id = self._write_xref_table(new_xref_entries)
            new_size = max(size - 1, max_entry_id) + 1

            # Construct the PDF trailer
            self._write_trailer(pdf_reader, original_startxref, xref_start, new_size)

        return new_xref_entries

    def _write_objects(self, incremented_objects):
        """
        Serializes a collection of PDF objects to the output stream.

        This method iterates through the provided objects, writes them to the
        stream in the standard PDF object format (``ID 0 obj ... endobj``),
        and records the file pointer position (byte offset) for each object.

        :param incremented_objects: A dictionary mapping Object IDs (int) to the
                                    PDF objects (e.g., PageObject, DictionaryObject).
        :type incremented_objects: dict[tuple[int, int], Any]
        :return: A dictionary mapping Object IDs to their new byte offsets in the stream.
                 This is used to construct the XRef table.
        :rtype: dict[tuple[int, int], int]
        """
        output = self.output_stream
        output.write(b"\n")
        xref_entries = {}
        for (obj_id, obj_gen), obj_data in sorted(incremented_objects.items()):
            xref_entries[(obj_id, obj_gen)] = output.tell()
            output.write(b_(f"{str(obj_id)} {str(obj_gen)} obj"))
            obj_data.write_to_stream(output, None)
            output.write(b"\nendobj\n")

        return xref_entries

    def _write_xref_stream(self, pdf_reader, xref_entries, original_startxref, original_size):
        """
        Writes a fully compliant Cross-Reference (XRef) Stream to the output.

        As defined in the Adobe PDF Reference, Sixth Edition, version 1.7 (2006), Section 3.4.7,
        an XRef Stream replaces the older plain-text ``xref`` tables and trailer dictionary
        with a single binary stream object. This method handles the structural
        requirements of constructing this stream by:

        1. Grouping modified objects into contiguous chunks for the ``/Index`` array.
        2. Packing the byte offsets into a strictly formatted binary payload using a
           ``/W [1 4 2]`` layout (1-byte Type, 4-byte Offset, 2-byte Generation).
        3. Self-referencing the stream's own object ID and absolute byte offset.
        4. Merging standard trailer entries (like ``/Root`` and ``/Info``) into the
           stream dictionary and linking to the previous XRef section via the
           ``/Prev`` key to maintain the incremental update chain (Section 3.4.5).

        :param pdf_reader: The reader object of the original PDF. Used to extract
            essential trailer dictionary entries (e.g., ``/Root``, ``/Info``, ``/ID``)
            to carry them forward into this stream's dictionary.
        :type pdf_reader: PdfReader
        :param xref_entries: A dictionary mapping ``(object_id, generation)`` tuples
            to their absolute byte offsets in the newly appended data.
        :type xref_entries: dict[tuple[int, int], int]
        :param original_startxref: The absolute byte offset of the previous cross-reference
            section. This establishes the ``/Prev`` chain, allowing PDF parsers to
            safely traverse multiple incremental updates sequentially.
        :type original_startxref: int
        :param original_size: The ``/Size`` value from the original PDF's trailer. Used
            to determine the next available Object ID for this XRef stream and to
            update the total document size limit.
        :type original_size: int
        :return: None
        """
        output = self.output_stream

        xref_start_offset = output.tell()

        # Object 0 (Sentinel Entry):
        if (0, 65535) not in xref_entries:
            xref_entries[(0, 65535)] = 0

        # Get maximum object ID from the new xref entries
        max_obj_id = max([k[0] for k in xref_entries.keys()])

        # Calculate the ID for this XRef stream as it will be written as a new object (next available ID)
        current_highest_id = max(original_size - 1, max_obj_id)
        xref_stream_obj_id = current_highest_id + 1

        # Add the XRef Stream itself to the xref entries
        # XRef streams always have a generation of 0
        xref_entries[(xref_stream_obj_id, 0)] = xref_start_offset

        # Prepare the Stream Data (Hex Encoded)
        sorted_ids = sorted(xref_entries.keys())
        index_array = []
        stream_data_hex = []

        i = 0
        while i < len(sorted_ids):
            start_j = i
            # Check contiguous chunks using the Object ID
            while i + 1 < len(sorted_ids) and sorted_ids[i + 1][0] == sorted_ids[i][0] + 1:
                i += 1

            chunk_ids = sorted_ids[start_j: i + 1]

            # Add to /Index array: [First Object ID, Count]
            index_array.append(chunk_ids[0][0])
            index_array.append(len(chunk_ids))

            # Generate Data for this chunk
            for oid_tuple in chunk_ids:
                oid, ogen = oid_tuple

                # Append the object entry to the xref stream data.
                # Format ">B I H" packs 7 bytes in Big-Endian order (required for PDF streams):
                #  > : Big-endian byte order
                #  B : Unsigned char (1 byte)   -> Entry Type (0, 1, or 2)
                #  I : Unsigned int (4 bytes)   -> Byte Offset (or Next Free Object ID)
                #  H : Unsigned short (2 bytes) -> Generation Number
                if oid == 0:
                    # Required sentinel entry (Object 0) for the free object linked list.
                    # Packs: [Type=0 (Free), Next_Free_Obj=0 (End of list), Max_Generation=65535]
                    stream_data_hex.append(struct.pack(">B I H", 0, 0, 65535))
                else:
                    offset = xref_entries[oid_tuple]

                    # Type 1 entries define objects that are in use but are not compressed
                    # Packs: [Type=1, Absolute_Byte_Offset, Generation_Number]
                    stream_data_hex.append(struct.pack(">B I H", 1, offset, ogen))
            i += 1

        # Join data as raw bytes
        stream_content_bytes = b"".join(stream_data_hex)

        stream_length = len(stream_content_bytes)

        xref_stream_object = StreamObject()
        xref_stream_object._data = stream_content_bytes
        xref_stream_object.update({
            NameObject(TK.TYPE): NameObject("/XRef"),
            NameObject(TK.SIZE): NumberObject(xref_stream_obj_id + 1),
            NameObject(TK.ROOT): pdf_reader.trailer.raw_get(TK.ROOT),
            NameObject(TK.PREV): NumberObject(original_startxref),

            # /W defines the byte widths for the 3 columns in the XRef stream: [Type, Offset, Generation]
            # - 1 byte for Type: The PDF spec only uses types 0, 1, and 2, which fit in one byte.
            # - 4 bytes for Offset: Supports byte offsets for PDFs up to ~4.29 GB.
            # - 2 bytes for Generation: Perfectly fits 65,535, the maximum allowed generation number.
            NameObject("/W"): ArrayObject([NumberObject(1), NumberObject(4), NumberObject(2)]),

            NameObject("/Index"): ArrayObject([NumberObject(x) for x in index_array]),
            NameObject("/Length"): NumberObject(stream_length)
        })
        if TK.INFO in pdf_reader.trailer:
            xref_stream_object[NameObject(TK.INFO)] = pdf_reader.trailer.raw_get(TK.INFO)
        if TK.ID in pdf_reader.trailer:
            xref_stream_object[NameObject(TK.ID)] = pdf_reader.trailer.raw_get(TK.ID)
        if TK.ENCRYPT in pdf_reader.trailer:
            xref_stream_object[NameObject(TK.ENCRYPT)] = pdf_reader.trailer.raw_get(TK.ENCRYPT)

        output.write(b_(f"{xref_stream_obj_id} 0 obj\n"))
        xref_stream_object.write_to_stream(output, None)
        output.write(b"\nendobj\n")

        # Trailer / EOF
        output.write(b_(f"startxref\n{xref_start_offset}\n%%EOF\n"))

    def _write_xref_table(self, xref_entries):
        """
        Writes the Cross-Reference (XRef) table to the output stream.

        This method formats the table according to ISO 32000-1, creating subsections
        as needed for the provided object entries.

        :param xref_entries: A dictionary mapping Object IDs to their byte offsets.
        :return: A tuple containing the byte offset of the 'xref' keyword and the
                 maximum written object ID.
        :rtype: tuple[int, int]
        """
        output = self.output_stream

        # ----------------------------------------------------------------------
        # XRef CONSTRUCTIONS (Adobe PDF Reference, Sixth Edition, version 1.7 (2006), Section 7.5.4)
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
        if (0, 65535) not in xref_entries:
            xref_entries[(0, 65535)] = 0

        sorted_ids = sorted(xref_entries.keys())
        i = 0
        while i < len(sorted_ids):
            start_j = i
            while i + 1 < len(sorted_ids) and sorted_ids[i + 1][0] == sorted_ids[i][0] + 1:
                i += 1

            chunk_ids = sorted_ids[start_j: i + 1]
            start_id = chunk_ids[0][0]
            output.write(b_(f"{start_id} {len(chunk_ids)}\n"))
            for obj_tuple in chunk_ids:
                oid, ogen = obj_tuple
                if oid == 0:
                    output.write(b_(f"{0:0>10} {65535:0>5} f \n"))
                else:
                    offset = xref_entries[obj_tuple]
                    output.write(b_(f"{offset:0>10} {ogen:0>5} n \n"))

            i += 1

        return xref_start, sorted_ids[-1][0]

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

        # --------------------------------------------------------------------------------------------
        # TRAILER CONSTRUCTION (Adobe PDF Reference, Sixth Edition, version 1.7 (2006), Section 7.5.5)
        # --------------------------------------------------------------------------------------------
        # The trailer dictionary allows the PDF reader to quickly locate key
        # document structures. For an Incremental Update, it must:
        # 1. Point to the Catalog (/Root) and Metadata (/Info) of the original file.
        # 2. Define the total number of objects (/Size) including the new additions.
        # 3. Chain back to the previous XRef table via the /Prev key, preserving
        #    the document's revision history.
        # 4. Replicate critical security identifiers (/ID and /Encrypt) to maintain
        #    file integrity and access permissions.
        # --------------------------------------------------------------------------------------------
        output.write(b"trailer\n")
        trailer = DictionaryObject()
        trailer.update(
            {
                NameObject(TK.SIZE): NumberObject(size),
                NameObject(TK.ROOT): pdf_reader.trailer.raw_get(TK.ROOT),
                NameObject(TK.PREV): NumberObject(original_startxref)
            }
        )
        if TK.INFO in pdf_reader.trailer:
            trailer[NameObject(TK.INFO)] = pdf_reader.trailer.raw_get(TK.INFO)
        if TK.ID in pdf_reader.trailer:
            trailer[NameObject(TK.ID)] = pdf_reader.trailer.raw_get(TK.ID)
        if TK.ENCRYPT in pdf_reader.trailer:
            trailer[NameObject(TK.ENCRYPT)] = pdf_reader.trailer.raw_get(TK.ENCRYPT)

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

    def _sweep_indirect_references(self, pdf_reader: PdfFileReader, root, next_id) -> dict[tuple[int, int], Any]:
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
        :return: Newly added objects dict to be incremented at the end of the pdf
        :rtype: dict[tuple[int, int], Any]
        """
        incremented_objects = {}

        idnum_hash = {}
        stack = deque()
        discovered = set()
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
                data, next_id = self._resolve_indirect_object(pdf_reader, data, idnum_hash, incremented_objects, next_id)

                if str(data) not in discovered:
                    discovered.add(str(data))
                    real_obj = self._get_indirect_object_data(data, incremented_objects)
                    stack.append((real_obj, None, None, []))

            # Check if data has a parent and if it is a dict or an array update the value
            if isinstance(parent, (DictionaryObject, ArrayObject)):
                if isinstance(data, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    incremented_objects[(next_id, 0)] = data
                    data_hash = data.hash_value()
                    idnum_hash[data_hash] = IndirectObject(next_id, 0, None)
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
                        indirect_reference_obj = self._get_indirect_object_data(indirect_reference, incremented_objects)

                        if indirect_reference_obj is not None:
                            idnum_hash[
                                indirect_reference_obj.hash_value()
                            ] = indirect_reference

        return incremented_objects

    def _resolve_indirect_object(
            self,
            pdf_reader: PdfFileReader,
            data: IndirectObject,
            idnum_hash: dict[bytes, Any],
            incremented_objects: dict[tuple[int, int], Any],
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
        :param idnum_hash: A cache dictionary mapping object hashes to their resolved IndirectObjects.
        :param incremented_objects: The registry of new objects for the incremental update.
        :param next_id: The next available Object ID.
        :return: A tuple containing the resolved ``IndirectObject`` and the (possibly incremented) ``next_id``.
        :rtype: tuple[IndirectObject, int]
        :raises ValueError: If the underlying PDF stream is closed.
        """
        if hasattr(data.pdf, "stream") and data.pdf.stream.closed:
            raise ValueError(f"I/O operation on closed file: {data.pdf.stream.name}")

        real_obj = self._get_indirect_object_data(data, incremented_objects)

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
        else:  # This is new incremented object in this PDF
            incremented_objects[(next_id, 0)] = real_obj
            idnum_hash[hash_value] = IndirectObject(next_id, 0, None)
            next_id += 1

        return idnum_hash[hash_value], next_id

    def _get_indirect_object_data(self, indirect_obj, incremented_objects):
        """
        Resolves an indirect reference into its actual underlying PDF object.

        This helper method retrieves the real data behind the reference by checking two distinct locations:

        1. **Original PDF**: If the reference is tied to an existing, loaded document
           (i.e., ``indirect_obj.pdf`` is not None), it fetches the original object
           directly from that reader or writer.
        2. **Incremental Update Dictionary**: If the reference lacks a PDF reader attribute,
           it means it's a newly created or modified object. The method then retrieves
           the actual data from the ``incremented_objects`` tracking dictionary using
           the object's ID and generation number.

        :param indirect_obj: The indirect reference object that needs to be resolved.
        :type indirect_obj: IndirectObject
        :param incremented_objects: A dictionary mapping ``(object_id, generation)``
            tuples to newly created or modified objects waiting to be written to the pdf.
        :type incremented_objects: dict[tuple[int, int], Any]
        :return: The resolved PDF object (e.g., ``DictionaryObject``,
            ``StreamObject``, ``ArrayObject``, etc.).
        :rtype: Any
        """
        if indirect_obj.pdf:
            return indirect_obj.pdf.get_object(indirect_obj)
        else:
            return incremented_objects[(indirect_obj.idnum, indirect_obj.generation)]
