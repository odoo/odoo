import io
import logging
import datetime
import math
import uuid
from typing import Any

from odoo.tools import mute_logger
from odoo.tools.pdf import (
    PdfFileReader,
    PdfObject,
    IndirectObject,
    NullObject,
    ArrayObject,
    DictionaryObject,
    NameObject,
    BooleanObject,
    NumberObject,
    RectangleObject,
    TextStringObject,
    DecodedStreamObject as StreamObject,
)

from .constants import TrailerKeys as TK, PageAttributes as PG
from .incremental_writer import IncrementalWriter

_logger = logging.getLogger(__name__)


def get_page_media_box(page) -> RectangleObject:
    """ Returns the page's ``/MediaBox``, falling back to US Letter when absent.

    ISO 32000-1:2008 (Section 7.7.3.3) requires a ``/MediaBox`` on every page (own or
    inherited), but some PDFs omit it entirely. Assume US Letter instead of crashing.

    :param page: The page object to read the media box from.
    """
    try:
        return page.mediabox
    except (TypeError, AssertionError):
        return RectangleObject((0, 0, 612, 792))


def outer_bounds(rect) -> tuple[int, int, int, int]:
    """ Returns the smallest integer bounding box ``(xmin, ymin, xmax, ymax)`` that completely encloses ``rect``.

    Coordinates are automatically sorted to handle any corner order. The minimum edges
    are rounded down (floor) and maximum edges are rounded up (ceil) to ensure no
    fractional parts of the original rectangle are cropped out.

    :param rect: A sequence of 4 coordinates ``(x_0, y_0, x_1, y_1)`` representing any two opposite corners.
    :return: A normalized tuple of 4 outward-rounded integer coordinates.
    """
    x0, x1 = sorted((float(rect[0]), float(rect[2])))
    y0, y1 = sorted((float(rect[1]), float(rect[3])))
    return (math.floor(x0), math.floor(y0), math.ceil(x1), math.ceil(y1))


def clip_to_bounds(rect, bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int] | None:
    """ Returns the mathematical intersection of ``rect`` and ``bounds``.

    Effectively crops ``rect`` so it does not extend outside of ``bounds``.
    If the two areas do not overlap, returns None.

    :param rect: The rectangle to restrict (any 4 coordinates).
    :param bounds: The strict boundary rectangle ``(xmin, ymin, xmax, ymax)`` to stay within.
    :return: A new tuple of clipped integer coordinates, or None.
    """
    x0, y0, x1, y1 = outer_bounds(rect)
    clipped = (max(x0, bounds[0]), max(y0, bounds[1]), min(x1, bounds[2]), min(y1, bounds[3]))

    return clipped if clipped[0] < clipped[2] and clipped[1] < clipped[3] else None


class IndirectObjectsWrapper:
    """ Registry for tracking new PDF objects and their indirect references.
    Assigns IDs and resolves IndirectObjects safely.

    The IDs are internal handles. So every registered object is reassigned a final ID from
    the target PDF by :meth:`IncrementalPdfMerge._resolve_indirect_object`, so they never
    reach the written file and cannot collide with the original PDF's IDs.
    """

    def __init__(self) -> None:
        # The index is the object ID, so ID 0 holds a dead cell. A PDF never assigns it,
        # it is the head of the free-object list.
        self.objects = [None]

    def add_object(self, obj: PdfObject) -> IndirectObject:
        """ Registers a new object and points its indirect_reference attribute to itself. """
        obj.indirect_reference = IndirectObject(len(self.objects), 0, self)
        self.objects.append(obj)

        return obj.indirect_reference

    def get_object(self, indirect_reference: int | IndirectObject) -> PdfObject:
        """ Resolves an indirect reference back to its underlying PDF raw object. """
        if isinstance(indirect_reference, int):
            obj = self.objects[indirect_reference]
        elif indirect_reference.pdf != self:
            raise ValueError("Wrapper must be self")
        else:
            obj = self.objects[indirect_reference.idnum]
        return obj


class IncrementalPdfMerge:
    """ A utility class that appends new content to an existing PDF via an Incremental Update (ISO 32000-1:2008, Section 7.5.6),
    without altering the original PDF bytes.

    (Ref: ISO 32000-1:2008 / https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)

    :param pdf_raw: The binary content of the original PDF file.
    """

    def __init__(self, pdf_raw: bytes) -> None:
        """ Loads the PDF and seeks to EOF to prepare for appending modifications. """
        self.writer = IncrementalWriter(pdf_raw)

    def get_output_stream_value(self) -> bytes:
        """ Returns the full binary content of the stream. """
        return self.writer.get_output_stream_value()

    def merge_pdf_regions_as_annotations(
            self,
            overlay_pdf: PdfFileReader,
            overlay_regions: dict[int, list[tuple[float, float, float, float]]],
            annotations_title: str = "overlay"
    ) -> None:
        """ Merges the content of an overlay PDF onto the current PDF output stream as stamp annotations
        (ISO 32000-1:2008, Section 7.5.6).

        :param overlay_pdf: The content to be overlaid.
        :param overlay_regions: Page index mapped to the rectangles of the overlay to expose, in page
            coordinates. Pages without a rectangle keep their annotations untouched.
        :param annotations_title: Name assigned to the created annotations.
        """
        pdf_reader, incremented_objects = self._annotate_pdf_regions(overlay_pdf, annotations_title, overlay_regions)

        self.write_incremented_pdf(pdf_reader, incremented_objects)

    def normalize_pages_annotations_to_indirect(self):
        """ Ensures every page's ``/Annots`` entry is an indirect object (e.g., ``/Annots 50 0 R``),
        creating an empty array indirect object if the entry is missing. Runs as a standalone incremental update.
        """

        pdf_reader = PdfFileReader(io.BytesIO(self.get_output_stream_value()), strict=False)
        incremented_objects = {}

        next_id = self.writer.get_next_object_id(pdf_reader)

        for page_index, page in enumerate(pdf_reader.pages):
            try:
                raw_annots = page.raw_get(PG.ANNOTS)
            except KeyError:
                raw_annots = None
            if not isinstance(raw_annots, IndirectObject):
                if raw_annots is None:
                    raw_annots = ArrayObject()

                incremented_objects[next_id, 0] = raw_annots
                raw_annots_ref = IndirectObject(next_id, 0, None)
                page[NameObject(PG.ANNOTS)] = raw_annots_ref
                next_id += 1

                page_ref_id = page.indirect_reference.idnum
                page_ref_gen = page.indirect_reference.generation
                incremented_objects[page_ref_id, page_ref_gen] = page
                self.update_cached_indirect_object(pdf_reader, page_ref_gen, page_ref_id, page)

        self.write_incremented_pdf(pdf_reader, incremented_objects, sweep_new_indirect_objects=False)

    def _annotate_pdf_regions(
            self,
            overlay_pdf: PdfFileReader,
            annotations_title: str,
            overlay_regions: dict[int, list[tuple[float, float, float, float]]],
    ) -> tuple[PdfFileReader, dict[tuple[int, int], Any]]:
        """ Embeds overlay_pdf content as locked Stamp Annotations (ISO 32000-1:2008, Section 12.5)
        on each page, without touching the base page's ``/Contents`` stream.

        The page's drawing is embedded once and every region gets its own annotation exposing it,
        so a region is never covered by an annotation belonging to another one.

        :param overlay_pdf: The visual content to be stamped.
        :param annotations_title: The title (``/T``) assigned to the stamp annotations.
        :param overlay_regions: Page index mapped to the rectangles of the overlay to expose, in page coordinates.
        :return: A tuple of the base ``PdfFileReader`` and a dict of modified objects keyed by ``(id, generation)``.
        """
        pdf_reader = PdfFileReader(io.BytesIO(self.get_output_stream_value()), strict=False)
        indirect_obj_wrapper = IndirectObjectsWrapper()  # A temporary Wrapper for new objects, useful for the indirect sweep
        incremented_objects = {}

        for page_index, page in enumerate(pdf_reader.pages):
            media_box = outer_bounds(get_page_media_box(page))
            regions = [clipped for region in overlay_regions.get(page_index, [])
                       if (clipped := clip_to_bounds(region, media_box))]
            if not regions:
                continue

            overlay_page = overlay_pdf.pages[page_index]

            content_stream = overlay_page.get_contents()
            if content_stream is None:
                continue

            overlay_resources = overlay_page.get(PG.RESOURCES, DictionaryObject())

            # Create the Appearance Stream XObject (Section 8.10): Extracts the raw content stream and
            # resources from the overlay page and wraps them in a Form XObject. It holds the drawing of
            # the whole page and is shared by every region below.
            page_overlay_ref = indirect_obj_wrapper.add_object(
                self._build_form_xobject(content_stream.get_data(), media_box, overlay_resources))

            annot_refs = []
            for region_index, region in enumerate(regions):
                # Each region is exposed through its own Form XObject whose ``/BBox`` equals the
                # annotation ``/Rect``. Without a ``/Matrix``, the appearance then maps one to one
                # (Section 12.5.5): the shared drawing paints at its original page coordinates and
                # is clipped to the region.
                region_overlay = self._build_form_xobject(b"q /X0 Do Q", region, DictionaryObject({
                    NameObject("/XObject"): DictionaryObject({NameObject("/X0"): page_overlay_ref}),
                }))

                # Create the Stamp Annotation (Section 12.5.6.12): Create a ``/Stamp`` annotation
                # dictionary locked via ``/F 196`` (Print, NoZoom, NoRotate, ReadOnly),
                # ``/Locked``, and ``/LockedContents`` flags. It also injects essential
                # tracking metadata (``/NM`` UUID, ``/M`` modification date).
                annot_dict = DictionaryObject()
                annot_dict.update({
                    NameObject("/Type"): NameObject("/Annot"),
                    NameObject("/Subtype"): NameObject("/Stamp"),
                    NameObject("/T"): TextStringObject(f"{annotations_title}_page_{page_index}_{region_index}"),
                    NameObject("/Rect"): ArrayObject([NumberObject(coordinate) for coordinate in region]),
                    NameObject("/F"): NumberObject(196),
                    NameObject("/Locked"): BooleanObject(True),
                    NameObject("/LockedContents"): BooleanObject(True),
                    # Appearance Stream (Section 12.5.5): Assigns the Form XObject to the
                    # normal appearance state (``/AP << /N ... >>``) of the annotation.
                    NameObject("/AP"): DictionaryObject({
                        NameObject("/N"): indirect_obj_wrapper.add_object(region_overlay)
                    }),
                    NameObject("/P"): page.indirect_reference,
                    NameObject("/NM"): TextStringObject(str(uuid.uuid4())),
                    NameObject("/M"): TextStringObject(datetime.datetime.now(datetime.timezone.utc).strftime("D:%Y%m%d%H%M%SZ"))
                })
                annot_refs.append(indirect_obj_wrapper.add_object(annot_dict))

            # Attach the Annotations to the Original Page
            try:
                raw_annots = page.raw_get(PG.ANNOTS)
            except KeyError:
                raw_annots = None
            if isinstance(raw_annots, IndirectObject):
                annots_array = raw_annots.get_object()
                annots_array.extend(annot_refs)
                raw_id = raw_annots.idnum
                raw_gen = raw_annots.generation
                incremented_objects.setdefault((raw_id, raw_gen), annots_array)
                self.update_cached_indirect_object(pdf_reader, raw_gen, raw_id, annots_array)
            else:
                if raw_annots is None:
                    raw_annots = ArrayObject()

                raw_annots.extend(annot_refs)
                page[NameObject(PG.ANNOTS)] = raw_annots

                page_ref_id = page.indirect_reference.idnum
                page_ref_gen = page.indirect_reference.generation
                incremented_objects[page_ref_id, page_ref_gen] = page
                # Invalidate cache and cache new page reference so it would be seen while sweeping indirect references later on
                self.update_cached_indirect_object(pdf_reader, page_ref_gen, page_ref_id, page)

        return pdf_reader, incremented_objects

    @staticmethod
    def _build_form_xobject(data: bytes, bbox: tuple[int, int, int, int], resources: DictionaryObject) -> StreamObject:
        """ Wraps drawing operators in a Form XObject (ISO 32000-1:2008, Section 8.10) clipped to ``bbox``.

        :param data: The raw drawing operators.
        :param bbox: The ``/BBox`` the operators are clipped to, in the form coordinate space.
        :param resources: The ``/Resources`` the operators refer to.
        """
        form_xobject = StreamObject()
        form_xobject._data = data
        form_xobject.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/FormType"): NumberObject(1),
            NameObject("/BBox"): ArrayObject([NumberObject(coordinate) for coordinate in bbox]),
            NameObject("/Resources"): resources,
        })

        return form_xobject

    @staticmethod
    def update_cached_indirect_object(pdf_reader: PdfFileReader, obj_gen: int, obj_id: int, obj: Any) -> None:
        """
        Caches an indirect object into the given PDF reader's internal cache.

        This method acts as a wrapper around the reader's `cache_indirect_object`
        method to intentionally suppress noisy "Overwriting cache" warnings
        generated by the PyPDF2 or pypdf libraries.

        :param pdf_reader: The PDF reader instance where the object will be cached.
        :param obj_gen: The generation number of the PDF indirect object.
        :param obj_id: The ID number of the PDF indirect object.
        :param obj: The actual PDF object data to be cached.
        """
        with mute_logger('PyPDF2'), mute_logger('pypdf'):
            pdf_reader.cache_indirect_object(obj_gen, obj_id, obj)

    def write_incremented_pdf(self, pdf_reader, incremented_objects, sweep_new_indirect_objects=True):
        """ Discovers new objects (optionally) and delegates the actual write to the
        :class:`~odoo.tools.pdf.incremental_writer.IncrementalWriter`.

        :param pdf_reader: The reader instance representing the current PDF state.
        :param incremented_objects: Modified objects keyed by ``(object_id, generation)``.
        :param sweep_new_indirect_objects: When ``True``, traverses the object graph from ``/Root``
            to discover and register new objects that weren't explicitly tracked.
        """
        if not incremented_objects:
            return

        if sweep_new_indirect_objects:
            next_id = self.writer.get_next_object_id(pdf_reader)
            catalog = pdf_reader.trailer[TK.ROOT]
            new_objects = self._traverse_incremented_objects(pdf_reader, catalog, next_id)
            for key, val in new_objects.items():
                incremented_objects[key] = val

        return self.writer.write_incremental_update(pdf_reader, incremented_objects)

    def _traverse_incremented_objects(self, pdf_reader: PdfFileReader, root: DictionaryObject | ArrayObject, next_id: int) -> dict[tuple[int, int], Any]:
        """ Recursively traverses the PDF object graph to identify new objects and update
        references.

        This method performs a **Depth-First Search (DFS)** starting from the provided
        ``root`` object. Its primary goals are:

        1.  **Discovery:** Identify all reachable objects (dictionaries, arrays, streams).
        2.  **Resolution:** Differentiate between existing objects (from the original PDF)
            and new objects (from the overlay).
        3.  **Remapping:** Assign valid Object IDs to new objects using ``_resolve_indirect_object``.
        4.  **Pointer Fixup:** If a child object is remapped to a new ID, this method updates
            the parent container (Dictionary or Array) to point to the new reference.

        :param pdf_reader: The reader instance for the original source PDF.
        :param root: The starting point of the traversal (usually the Document Catalog).
        :param next_id: The first available Object ID to use for new objects.
        :return: Newly added objects dict to be incremented at the end of the pdf
        """
        incremented_objects = {}

        idnum_hash = {}
        stack = []
        discovered = set()
        parent = None
        grant_parents = []
        key_or_id = None

        stack.append((root, parent, key_or_id, grant_parents))

        while stack:
            data, parent, key_or_id, grant_parents = stack.pop()

            if isinstance(data, DictionaryObject):
                for key, value in data.items():
                    stack.append(
                        (
                            value,
                            data,
                            key,
                            [] if parent is None else grant_parents + [parent],
                        )
                    )
            elif isinstance(data, ArrayObject):
                for idx, value in enumerate(data):
                    stack.append(
                        (
                            value,
                            data,
                            idx,
                            [] if parent is None else grant_parents + [parent],
                        )
                    )
            elif isinstance(data, IndirectObject):
                data, next_id = self._resolve_indirect_object(pdf_reader, data, idnum_hash, incremented_objects, next_id)

                data_key = (data.idnum, data.generation)
                if data_key not in discovered:
                    discovered.add(data_key)
                    real_obj = self._get_indirect_object_data(data, incremented_objects)
                    stack.append((real_obj, None, None, []))

            if isinstance(parent, (DictionaryObject, ArrayObject)):
                if isinstance(data, StreamObject):
                    # a dictionary value is a stream.  streams must be indirect
                    # objects, so we need to change this value.
                    incremented_objects[next_id, 0] = data
                    data_hash = data.hash_value()
                    idnum_hash[data_hash] = IndirectObject(next_id, 0, None)
                    next_id += 1
                    data = idnum_hash[data_hash]

                update_hashes = []

                old_data = parent[key_or_id] if isinstance(parent, ArrayObject) else parent.raw_get(key_or_id)
                if old_data != data:
                    update_hashes = [parent.hash_value()] + [
                        grant_parent.hash_value() for grant_parent in grant_parents
                    ]
                    parent[key_or_id] = data

                for old_hash in update_hashes:
                    indirect_reference = idnum_hash.pop(old_hash, None)

                    if indirect_reference is not None:
                        indirect_reference_obj = self._get_indirect_object_data(indirect_reference, incremented_objects)

                        if indirect_reference_obj is not None:
                            idnum_hash[indirect_reference_obj.hash_value()] = indirect_reference

        return incremented_objects

    def _resolve_indirect_object(
            self,
            pdf_reader: PdfFileReader,
            data: IndirectObject,
            idnum_hash: dict[bytes, Any],
            incremented_objects: dict[tuple[int, int], Any],
            next_id: int
    ) -> IndirectObject:
        """ Resolves an indirect reference to its final Object ID. Preserves the original ID for existing
        objects (from ``pdf_reader``) and assigns a new one for foreign objects.
        Uses ``idnum_hash`` to deduplicate identical objects.

        :param data: The indirect reference to resolve.
        :param pdf_reader: The reader for the original PDF.
        :param idnum_hash: Cache mapping object hashes to their resolved ``IndirectObject``.
        :param incremented_objects: Registry of new objects for the incremental update.
        :param next_id: The next available Object ID.
        :return: A tuple of the resolved ``IndirectObject`` and the (possibly incremented) ``next_id``.
        :raises ValueError: If the underlying PDF stream is closed.
        """
        if hasattr(data.pdf, "stream") and data.pdf.stream.closed:
            raise ValueError(f"I/O operation on closed file: {data.pdf.stream.name}")

        real_obj = self._get_indirect_object_data(data, incremented_objects)

        if real_obj is None:
            _logger.warning(
                "Unable to resolve [%s: %s], returning NullObject instead",
                data.__class__.__name__,
                data,
            )
            real_obj = NullObject()

        hash_value = real_obj.hash_value()

        if hash_value in idnum_hash:
            return idnum_hash[hash_value], next_id

        if data.pdf == pdf_reader:
            idnum_hash[hash_value] = IndirectObject(data.idnum, data.generation, pdf_reader)
        else:  # This is new incremented object in this PDF
            incremented_objects[next_id, 0] = real_obj
            idnum_hash[hash_value] = IndirectObject(next_id, 0, None)
            next_id += 1

        return idnum_hash[hash_value], next_id

    def _get_indirect_object_data(self, indirect_obj, incremented_objects):
        """ Retrieves the underlying PDF object for an indirect reference, checking the original
        PDF reader first and falling back to ``incremented_objects`` for new or modified objects.
        """
        if indirect_obj.pdf:
            return indirect_obj.pdf.get_object(indirect_obj)
        else:
            return incremented_objects[indirect_obj.idnum, indirect_obj.generation]
