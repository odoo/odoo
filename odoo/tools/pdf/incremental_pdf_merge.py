import io
import logging
import datetime
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
    TextStringObject,
    DecodedStreamObject as StreamObject,
)

from .constants import TrailerKeys as TK, PageAttributes as PG
from .incremental_writer import IncrementalWriter

_logger = logging.getLogger(__name__)


class IndirectObjectsWrapper:
    """ Registry for tracking new PDF objects and their indirect references.
    Assigns IDs and resolves IndirectObjects safely.
    """

    def __init__(self, start_id=1) -> None:
        """
        :param start_id: Start ID. Set to the original PDF's /Size to prevent collisions.
        """
        self.objects_map = {}
        self.next_id = start_id

    def add_object(self, obj: PdfObject) -> IndirectObject:
        """ Registers a new object and points its indirect_reference attribute to itself. """
        self.objects_map[self.next_id] = obj
        obj.indirect_reference = IndirectObject(self.next_id, 0, self)
        self.next_id += 1

        return obj.indirect_reference

    def get_object(self, indirect_reference: int | IndirectObject) -> PdfObject:
        """ Resolves an indirect reference back to its underlying PDF raw object. """
        if isinstance(indirect_reference, int):
            obj = self.objects_map[indirect_reference]
        elif indirect_reference.pdf != self:
            raise ValueError("Wrapper must be self")
        else:
            obj = self.objects_map[indirect_reference.idnum]
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

    def merge_pdf_as_annotation(
            self,
            overlay_pdf: PdfFileReader,
            overlay_pages: set[int] | None = None,
            annotations_title: str = "overlay"
    ) -> None:
        """ Merges the content of an overlay PDF onto the current PDF output stream as a stamp annotation
        (ISO 32000-1:2008, Section 7.5.6).

        :param overlay_pdf: The content to be overlaid.
        :param overlay_pages: Optional set of page indices to overlay; if None, all pages are overlaid.
        :param annotations_title: Name assigned to the created annotation.
        """
        pdf_reader, incremented_objects = self._merge_pdf_pages_as_annotation(overlay_pdf, annotations_title, overlay_pages)

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

    def _merge_pdf_pages_as_annotation(
            self,
            overlay_pdf: PdfFileReader,
            annotations_title: str,
            overlay_pages: set[int] | None = None,
    ) -> tuple[PdfFileReader, dict[tuple[int, int], Any]]:
        """ Embeds overlay_pdf content as a locked Stamp Annotation (ISO 32000-1:2008, Section 12.5)
        on each page, without touching the base page's ``/Contents`` stream.

        :param overlay_pdf: The visual content to be stamped.
        :param annotations_title: The title (``/T``) assigned to the stamp annotation.
        :param overlay_pages: Optional set of page indices to overlay; if None, all pages are overlaid.
        :return: A tuple of the base ``PdfFileReader`` and a dict of modified objects keyed by ``(id, generation)``.
        """
        pdf_reader = PdfFileReader(io.BytesIO(self.get_output_stream_value()), strict=False)
        indirect_obj_wrapper = IndirectObjectsWrapper()  # A temporary Wrapper for new objects, useful for the indirect sweep
        incremented_objects = {}

        for page_index, page in enumerate(pdf_reader.pages):
            if overlay_pages and page_index not in overlay_pages:
                continue

            overlay_page = overlay_pdf.pages[page_index]

            content_stream = overlay_page.get_contents()
            if content_stream is None:
                continue

            overlay_resources = overlay_page.get(PG.RESOURCES, DictionaryObject())
            media_box = page.mediabox

            # Create the Appearance Stream XObject (Section 8.10): Extracts the raw content stream and
            # resources from the overlay page and wraps them in a Form XObject.
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

            # Create the Stamp Annotation (Section 12.5.6.12): Create a ``/Stamp`` annotation
            # dictionary locked via ``/F 196`` (Print, NoZoom, NoRotate, ReadOnly),
            # ``/Locked``, and ``/LockedContents`` flags. It also injects essential
            # tracking metadata (``/NM`` UUID, ``/M`` modification date).
            appearance_stream_ref = indirect_obj_wrapper.add_object(appearance_stream)
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
                # Appearance Stream (Section 12.5.5): Assigns the Form XObject to the
                # normal appearance state (``/AP << /N ... >>``) of the annotation.
                NameObject("/AP"): DictionaryObject({
                    NameObject("/N"): appearance_stream_ref
                }),
                NameObject("/P"): page.indirect_reference,
                NameObject("/NM"): TextStringObject(str(uuid.uuid4())),
                NameObject("/M"): TextStringObject(datetime.datetime.now(datetime.timezone.utc).strftime("D:%Y%m%d%H%M%SZ"))
            })

            # Attach the Annotation to the Original Page
            annot_ref = indirect_obj_wrapper.add_object(annot_dict)
            try:
                raw_annots = page.raw_get(PG.ANNOTS)
            except KeyError:
                raw_annots = None
            if isinstance(raw_annots, IndirectObject):
                annots_array = raw_annots.get_object()
                annots_array.append(annot_ref)
                raw_id = raw_annots.idnum
                raw_gen = raw_annots.generation
                incremented_objects.setdefault((raw_id, raw_gen), annots_array)
                self.update_cached_indirect_object(pdf_reader, raw_gen, raw_id, annots_array)
            else:
                if raw_annots is None:
                    raw_annots = ArrayObject()

                raw_annots.append(annot_ref)
                page[NameObject(PG.ANNOTS)] = raw_annots

                page_ref_id = page.indirect_reference.idnum
                page_ref_gen = page.indirect_reference.generation
                incremented_objects[page_ref_id, page_ref_gen] = page
                # Invalidate cache and cache new page reference so it would be seen while sweeping indirect references later on
                self.update_cached_indirect_object(pdf_reader, page_ref_gen, page_ref_id, page)

        return pdf_reader, incremented_objects

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
