import io
import logging
from typing import cast, Any
from collections import deque

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
    ByteStringObject,
    ContentStream,
    DecodedStreamObject as StreamObject,
)

from PyPDF2 import PageObject

_logger = logging.getLogger(__name__)

class TrailerKeys:
    """
    Constants representing standard keys used in the PDF Trailer dictionary.

    These keys are defined in **ISO 32000-1 (Section 7.5.5)** and are used
    to locate critical parts of the document structure.
    """
    ROOT = "/Root"  # Points to the Document Catalog (root of the object graph)
    ENCRYPT = "/Encrypt"  # Points to the Encryption Dictionary (if protected)
    ID = "/ID"  # An array of two byte-strings forming the unique file identifier
    INFO = "/Info"  # Points to the Information Dictionary (Metadata: Author, Title...)
    SIZE = "/Size"  # Total number of objects in the document's XRef table
    PREV = "/Prev"  # Byte offset to the previous XRef table (essential for incremental updates)

TK = TrailerKeys

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
        pdf_reader, incremented_objects = self._merge_pdf_pages(overlay_pdf)
        self._write_incremented_pdf(pdf_reader, incremented_objects)

    def overlay_pdf_as_annotation(self, overlay_pdf: PdfFileReader) -> None:
        pdf_reader, incremented_objects = self._overlay_pdf_pages_as_annotation(overlay_pdf)
        self._write_incremented_pdf(pdf_reader, incremented_objects)

    def _merge_pdf_pages(self, overlay_pdf: PdfFileReader) -> tuple[PdfFileReader, dict[int, Any]]:
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
            page.mergePage(overlay_pdf.pages[page_index])
            incremented_objects[page.indirect_reference.idnum] = page

        return pdf_reader, incremented_objects

    def _overlay_pdf_pages_as_annotation(self, overlay_pdf: PdfFileReader) -> tuple[PdfFileReader, dict[int, Any]]:
        # 1. Load the current output stream PDF bytes in memory
        pdf_reader = PdfFileReader(io.BytesIO(self.get_output_stream_value()), strict=False)

        # 2. Convert overlay pages to an annotations
        incremented_objects = {}
        for page_index in range(0, len(pdf_reader.pages)):
            page = pdf_reader.pages[page_index]
            page2 = overlay_pdf.pages[page_index]

            annot = self._convert_page_content_to_annotation_object(page2)
            if annot is None:
                continue

            new_annots = ArrayObject()
            if "/Annots" in page:
                annots = page["/Annots"]
                if isinstance(annots, ArrayObject):
                    for ref in annots:
                        new_annots.append(ref)

            writer = PdfFileWriter()  # A temporary PdfFileWriter used to wrap new objects
            ann_indirect_reference = writer._add_object(annot)
            new_annots.append(ann_indirect_reference)
            # page["/Annots"].append(writer._add_object(annot))
            page[NameObject("/Annots")] = new_annots

            incremented_objects[page.indirect_reference.idnum] = page

        return pdf_reader, incremented_objects

    def _convert_page_content_to_annotation_object(self, page):
        page_content = page.get_contents()
        if page_content is None:
            return

        page_content = ContentStream(page_content, page.pdf)
        page_content = PageObject._push_pop_gs(page_content, page.pdf)

        form = StreamObject()
        form._data = page_content.get_data()

        mb = page.mediabox

        bbox = ArrayObject([mb.left, mb.bottom, mb.right, mb.top])
        form.update({
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/FormType"): NumberObject(1),
            NameObject("/BBox"): bbox,
            NameObject("/Resources"): page.get("/Resources", DictionaryObject()),
        })

        rect = ArrayObject([ mb.left, mb.bottom, mb.right, mb.top ])
        annot = DictionaryObject()
        annot.update({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Stamp"),
            NameObject("/Rect"): rect,
            NameObject("/AP"): DictionaryObject({
                NameObject("/N"): form
            }),
            NameObject("/F"): NumberObject(4),  # Print flag
            NameObject("/P"): page.indirect_reference,
            NameObject("/Contents"): ByteStringObject(b_("Signature Stamp"))
        })

        return annot

    def _write_incremented_pdf(self, pdf_reader, incremented_objects):
        start_id = pdf_reader.trailer[TK.SIZE]
        original_startxref = self._find_last_startxref(self.get_output_stream_value())

        # We perform a recursive traversal starting from the Catalog (/Root) to
        # detect any newly created objects injected during the merge. These objects
        # are assigned valid, contiguous Object IDs to ensure they are correctly
        # indexed in the upcoming incremental XRef update. Additionally, this step
        # resolves circular references (e.g., objects pointing back to their parent
        # Pages), ensuring the integrity of the object graph.
        catalog = cast(DictionaryObject, pdf_reader.trailer[TK.ROOT])
        self._sweep_indirect_references(catalog, pdf_reader, incremented_objects, start_id)

        # 5. Write all objects to the output stream
        output = self.output_stream
        new_xref_entries = self._write_objects(output, incremented_objects)

        # 6. Generate Xref table
        xref_start, new_size = self._write_xref_table(output, new_xref_entries)

        # 7. Construct the PDF trailer
        self._write_trailer(output, pdf_reader, original_startxref, xref_start, new_size)

    def _write_objects(self, output, incremented_objects):
        new_xref_entries = {}
        for obj_id, obj_data in sorted(incremented_objects.items()):
            new_xref_entries[obj_id] = output.tell()
            output.write(b_(str(obj_id)) + b" 0 obj\n")
            obj_data.write_to_stream(output, None)
            output.write(b"\nendobj\n")

        return new_xref_entries

    def _write_xref_table(self, output, new_xref_entries):
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

    def _write_trailer(self, output, pdf_reader, original_startxref, xref_start, size):
        # 7. Construct the PDF trailer
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

    def _sweep_indirect_references(self, root, pdf_reader, incremented_objects, start_id) -> None:
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

        :param root: The starting point of the traversal (usually the Document Catalog).
        :type root: DictionaryObject or ArrayObject
        :param pdf_reader: The reader instance for the original source PDF.
        :type pdf_reader: PdfFileReader
        :param incremented_objects: A dictionary mapping new Object IDs to their content.
            This is updated in-place as new objects are discovered.
        :type incremented_objects: dict
        :param start_id: The first available Object ID to use for new objects.
        :type start_id: int
        :return: None
        """
        next_id = start_id

        idnum_hash = {}
        writer = PdfFileWriter()  # A temporary PdfFileWriter used to wrap new objects

        stack = deque()
        discovered = []
        parent = None
        grant_parents = []
        key_or_id = None

        # Start from root
        stack.append((root, parent, key_or_id, grant_parents))

        for key, real_obj in incremented_objects.items():
            hash_value = real_obj.hash_value()
            if hash_value not in idnum_hash:
                idnum_hash[hash_value] = IndirectObject(key, 0, pdf_reader)

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
                data, next_id = self._resolve_indirect_object(data, pdf_reader, writer, idnum_hash, incremented_objects, next_id)

                if str(data) not in discovered:
                    discovered.append(str(data))
                    # If the ID exists in 'incremented_objects', it is a newly created object.
                    # We must retrieve it from memory, as it does not exist in the original PDF.
                    stack.append((
                        data.get_object() if data.idnum not in incremented_objects else incremented_objects[data.idnum],
                        None,
                        None,
                        []
                    ))

            # Check if data has a parent and if it is a dict or an array update the value
            if isinstance(parent, (DictionaryObject, ArrayObject)):
                if isinstance(data, StreamObject):
                    # a dictionary value is a stream. streams must be indirect
                    # objects, so we need to change this value.
                    # since it's a creation of new indirect object
                    # we will append it as a new incremented object.
                    incremented_objects[next_id] = data
                    data_hash = data.hash_value()
                    idnum_hash[data_hash] = IndirectObject(next_id, 0, writer)
                    self._pdf_writer_append_obj(writer, data, next_id)
                    data = idnum_hash[data_hash]
                    next_id += 1

                update_hashes = []

                # Data changed and thus the hash value changed
                if parent[key_or_id] != data:
                    update_hashes = [parent.hash_value()] + [
                        grant_parent.hash_value() for grant_parent in grant_parents
                    ]
                    parent[key_or_id] = data

                # Update old hash value to new hash value
                for old_hash in update_hashes:
                    indirect_reference = idnum_hash.pop(old_hash, None)

                    if indirect_reference is not None:
                        # If the ID exists in 'incremented_objects', it is a newly created object.
                        # We must retrieve it from memory, as it does not exist in the original PDF.
                        indirect_reference_obj = indirect_reference.get_object() \
                            if indirect_reference.idnum not in incremented_objects \
                            else incremented_objects[indirect_reference.idnum]

                        if indirect_reference_obj is not None:
                            idnum_hash[
                                indirect_reference_obj.hash_value()
                            ] = indirect_reference

    def _resolve_indirect_object(
            self,
            data: IndirectObject,
            pdf_reader,
            writer,
            idnum_hash,
            incremented_objects,
            next_id
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

        real_obj = data.pdf.get_object(data) if data.idnum not in incremented_objects else incremented_objects[data.idnum]

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
        # This is new object in this pdf
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
