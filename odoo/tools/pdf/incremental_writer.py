import io
import struct

from odoo.tools.pdf import (
    PdfFileReader,
    ArrayObject,
    DictionaryObject,
    NameObject,
    NumberObject,
    DecodedStreamObject as StreamObject,
)

from .constants import TrailerKeys as TK


class IncrementalWriter:
    """ Low-level writer for PDF Incremental Updates (ISO 32000-1:2008, Section 7.5.6).

    (Ref: ISO 32000-1:2008 / https://opensource.adobe.com/dc-acrobat-sdk-docs/pdfstandards/PDF32000_2008.pdf)

    Manages the PDF output stream and appends incremental updates, including modified objects,
    an updated XRef table (or stream), and a new trailer, without changing the original PDF bytes.

    :param pdf_raw: The binary content of the original PDF file.
    """

    def __init__(self, pdf_raw: bytes) -> None:
        """ Loads the PDF and seeks to EOF to prepare for appending modifications. """
        self.output_stream = io.BytesIO(pdf_raw)
        self.output_stream.seek(0, io.SEEK_END)

    def get_output_stream_value(self) -> bytes:
        """ Returns the full binary content of the stream. """
        return self.output_stream.getvalue()

    def get_next_object_id(self, pdf_reader: PdfFileReader) -> int:
        """ Returns the PDF /Size limit (highest object ID + 1), which doubles as
        the next available object ID for new incremented objects.
        Calculates it mathematically if missing from the trailer.
        """
        # Trust that the trailer contain a size first (Standard behavior)
        size = pdf_reader.trailer.get(TK.SIZE)

        # If size is missing, it's a xref stream PDF, we need calculate size (Fall back for PDF 1.5+)
        if not size:
            all_ids = set(pdf_reader.xref_objStm.keys())
            for gen in pdf_reader.xref.values():
                all_ids.update(gen.keys())
            # default=0 guards against an empty set
            size = max(all_ids, default=0) + 1

        return size

    def write_incremental_update(self, pdf_reader: PdfFileReader, incremented_objects: dict) -> dict | None:
        """ Appends an Incremental Update section (ISO 32000-1:2008, Section 7.5.6) to the
        stream: serializes the modified objects, then writes the new XRef (table or stream)
        and trailer.

        :param pdf_reader: The reader instance representing the current PDF state.
        :param incremented_objects: Modified objects keyed by ``(object_id, generation)``.
        :return: The xref entries written, keyed by ``(object_id, generation)``, or
            ``None`` if there was nothing to write.
        """
        if not incremented_objects:
            return None

        original_startxref = self._find_last_startxref(self.get_output_stream_value())

        # Check if the original PDF uses an XRef stream
        # PyPDF strips /Type /XRef from the trailer dict.
        # Check the raw bytes at original_startxref: if it does not start with 'xref',
        # it is an object representing an XRef stream
        is_xref_stream = pdf_reader.trailer.get(TK.TYPE) == "/XRef"
        if not is_xref_stream:
            raw_data = self.get_output_stream_value()
            target_bytes = raw_data[original_startxref : original_startxref + 20].lstrip()
            if target_bytes and not target_bytes.startswith(b"xref"):
                is_xref_stream = True

        size = self.get_next_object_id(pdf_reader)

        new_xref_entries = self._write_objects(incremented_objects)

        if is_xref_stream:
            self._write_xref_stream(pdf_reader, new_xref_entries, original_startxref, size)
        else:
            xref_start, max_entry_id = self._write_xref_table(new_xref_entries)
            new_size = max(size - 1, max_entry_id) + 1
            self._write_trailer(pdf_reader, original_startxref, xref_start, new_size)

        return new_xref_entries

    def _write_objects(self, incremented_objects):
        """ Writes each incremented object block and returns its final byte offset mapping for the XRef. """
        output = self.output_stream
        output.write(b"\n")
        xref_entries = {}
        for (obj_id, obj_gen), obj_data in sorted(incremented_objects.items()):
            xref_entries[obj_id, obj_gen] = output.tell()
            output.write(f"{obj_id} {obj_gen} obj".encode("latin-1"))
            obj_data.write_to_stream(output, None)
            output.write(b"\nendobj\n")

        return xref_entries

    def _write_xref_stream(self, pdf_reader, xref_entries, original_startxref, original_size):
        """ Writes a binary XRef stream (ISO 32000-1:2008, Section 7.5.8) for an incremental update,
        replacing the older plain-text ``xref`` table and trailer with a single binary stream object.

        :param pdf_reader: Original PDF reader, used to carry forward core trailer entries.
        :param xref_entries: Maps ``(object_id, generation)`` to new absolute byte offsets.
        :param original_startxref: Byte offset of the previous xref section, set as the ``/Prev`` link.
        :param original_size: Previous trailer ``/Size``, used to assign this stream's object ID.
        """
        output = self.output_stream

        xref_start_offset = output.tell()

        # Object 0 (Sentinel Entry):
        if (0, 65535) not in xref_entries:
            xref_entries[0, 65535] = 0

        max_obj_id = max(k[0] for k in xref_entries)

        # Calculate the ID for this XRef stream as it will be written as a new object (next available ID)
        current_highest_id = max(original_size - 1, max_obj_id)
        xref_stream_obj_id = current_highest_id + 1

        # Add the XRef Stream itself to the xref entries
        # XRef streams always have a generation of 0
        xref_entries[xref_stream_obj_id, 0] = xref_start_offset

        sorted_ids = sorted(xref_entries.keys())
        index_array = []
        stream_data_hex = []

        i = 0
        while i < len(sorted_ids):
            start_j = i
            # Check contiguous chunks using the Object ID
            while i + 1 < len(sorted_ids) and sorted_ids[i + 1][0] == sorted_ids[i][0] + 1:
                i += 1

            chunk_ids = sorted_ids[start_j : i + 1]

            # Add to /Index array: [First Object ID, Count]
            index_array.append(chunk_ids[0][0])
            index_array.append(len(chunk_ids))

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

        output.write(f"{xref_stream_obj_id} 0 obj\n".encode("latin-1"))
        xref_stream_object.write_to_stream(output, None)
        output.write(b"\nendobj\n")

        output.write(f"startxref\n{xref_start_offset}\n%%EOF\n".encode("latin-1"))

    def _write_xref_table(self, xref_entries):
        """ Writes the Cross-Reference (XRef) table to the output stream. """
        output = self.output_stream

        # ISO 32000-1:2008 §7.5.4 - XRef table split into subsections for sparse Object ID ranges.
        xref_start = output.tell()
        output.write(b"xref\n")

        # Object 0: mandatory free-list sentinel (offset=0, gen=65535, type='f').
        if (0, 65535) not in xref_entries:
            xref_entries[0, 65535] = 0

        sorted_ids = sorted(xref_entries.keys())
        i = 0
        while i < len(sorted_ids):
            start_j = i
            while i + 1 < len(sorted_ids) and sorted_ids[i + 1][0] == sorted_ids[i][0] + 1:
                i += 1

            chunk_ids = sorted_ids[start_j : i + 1]
            start_id = chunk_ids[0][0]
            output.write(f"{start_id} {len(chunk_ids)}\n".encode("latin-1"))
            for obj_tuple in chunk_ids:
                oid, ogen = obj_tuple
                if oid == 0:
                    output.write(f"{0:0>10} {65535:0>5} f \n".encode("latin-1"))
                else:
                    offset = xref_entries[obj_tuple]
                    output.write(f"{offset:0>10} {ogen:0>5} n \n".encode("latin-1"))

            i += 1

        return xref_start, sorted_ids[-1][0]

    def _write_trailer(self, pdf_reader, original_startxref, xref_start, size):
        """ Writes the trailer dictionary and the final end-of-file markers.

        :param pdf_reader: The reader instance, used to copy original Root, Info, and ID.
        :param original_startxref: Byte offset of the previous XRef table, set as the ``/Prev`` chain link.
        :param xref_start: Byte offset of the newly written XRef table.
        :param size: Total number of objects in the updated PDF.
        """
        output = self.output_stream

        # ISO 32000-1:2008 §7.5.5 - Incremental update trailer: chains /Prev, carries forward /Root, /ID, /Encrypt.
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
        output.write(f"\nstartxref\n{xref_start}\n%%EOF\n".encode("latin-1"))

    def _find_last_startxref(self, data):
        """ Scans backwards to find the byte offset of the previously saved XRef block. """
        # Search from end of file for startxref
        idx = data.rfind(b"startxref")
        if idx == -1:
            return 0

        try:
            return int(data[idx:].splitlines()[1].strip())
        except (ValueError, IndexError) as e:
            raise ValueError("Malformed PDF: could not parse the last startxref offset.") from e
