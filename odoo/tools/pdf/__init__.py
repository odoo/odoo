import base64
import io
import re
import unicodedata
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import md5
from logging import getLogger
from typing import Any, TYPE_CHECKING
from zlib import compress, decompress, decompressobj

from PIL import Image, PdfImagePlugin

from odoo.libs.debug_log import DebugLog
from odoo.libs.text import reshape
from odoo.libs.parse_version import parse_version
from odoo.libs.iteration import SENTINEL
from odoo.tools.files import file_open

from . import _pypdf as pypdf

if TYPE_CHECKING:
    from collections.abc import Generator

from ._pypdf import PdfReader as PdfReaderBase
from ._pypdf import PdfWriter, create_string_object, errors, filters, generic
from pypdf.generic import (
    ArrayObject,
    BooleanObject,
    ByteStringObject,
    DecodedStreamObject,
    DictionaryObject,
    IndirectObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

PdfReadError = errors.PdfReadError
PdfStreamError = errors.PdfStreamError
DependencyError = errors.DependencyError


class PdfReader(PdfReaderBase):
    def __init__(
        self, stream: io.BytesIO | str, strict: bool = True, *args: Any, **kwargs: Any
    ) -> None:
        super().__init__(stream, strict, *args, **kwargs)


_logger = getLogger(__name__)
_debug = DebugLog(__name__)
DEFAULT_PDF_DATETIME_FORMAT = "D:%Y%m%d%H%M%S+00'00'"
REGEX_SUBTYPE_UNFORMATED = re.compile(r"^\w+/[\w-]+$")
REGEX_SUBTYPE_FORMATED = re.compile(r"^/\w+#2F[\w-]+$")
PDFA_ID_NAMESPACE = "http://www.aiim.org/pdfa/ns/id/"
RDF_NAMESPACE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"


_ = PdfImagePlugin.__name__


class BrandedFileWriter(PdfWriter):
    def write_stream(self, *args: Any, **kwargs: Any) -> None:
        self.add_metadata(
            {
                "/Creator": "Odoo",
                "/Producer": "Odoo",
            }
        )
        super().write_stream(*args, **kwargs)


def merge_pdf(pdf_data: list[bytes]) -> bytes:
    writer = BrandedFileWriter()
    with _debug.perf(
        "pdf.merge",
        documents=len(pdf_data),
        input_bytes=sum(len(document) for document in pdf_data),
    ) as span:
        for document in pdf_data:
            reader = PdfReader(io.BytesIO(document), strict=False)
            for page in range(len(reader.pages)):
                writer.add_page(reader.pages[page])

        with io.BytesIO() as _buffer:
            writer.write(_buffer)
            merged = _buffer.getvalue()
        span.set(pages=len(writer.pages), output_bytes=len(merged))
    return merged


def update_form_fields_pdf(writer: PdfWriter, form_fields: dict[str, Any]) -> None:

    writer.set_need_appearances_writer()

    for page_id in range(len(writer.pages)):
        page = writer.pages[page_id]
        writer.update_page_form_field_values(page, form_fields)


def rotate_pdf(pdf: bytes) -> bytes:
    writer = BrandedFileWriter()
    reader = PdfReader(io.BytesIO(pdf), strict=False)
    with _debug.perf("pdf.rotate", pages=len(reader.pages), input_bytes=len(pdf)):
        for page in reader.pages:
            page.rotate(90)
            writer.add_page(page)
        with io.BytesIO() as _buffer:
            writer.write(_buffer)
            return _buffer.getvalue()


def to_pdf_stream(attachment) -> io.BytesIO | None:
    if attachment_raw := attachment._get_pdf_raw():
        _debug.logic(
            "pdf.stream_source",
            attachment=attachment.id,
            source="pdf",
            size=len(attachment_raw),
        )
        return io.BytesIO(attachment_raw)

    raw = attachment._with_bin_size_disabled().raw
    if not raw:
        _logger.warning("%s has no raw data.", attachment)
        _debug.logic("pdf.stream_source", attachment=attachment.id, source="empty")
        return None

    stream = io.BytesIO(raw)
    if attachment.mimetype.startswith("image"):
        output_stream = io.BytesIO()
        with _debug.perf(
            "pdf.image_converted",
            attachment=attachment.id,
            mimetype=attachment.mimetype,
            size=len(raw),
        ):
            Image.open(stream).convert("RGB").save(output_stream, format="pdf")
        return output_stream
    _logger.warning(
        "mimetype (%s) not recognized for %s", attachment.mimetype, attachment
    )
    _debug.logic(
        "pdf.stream_source",
        attachment=attachment.id,
        source="unsupported",
        mimetype=attachment.mimetype,
    )
    return None


def extract_page(attachment, num_page=0) -> io.BytesIO | None:
    pdf_stream = to_pdf_stream(attachment)
    if not pdf_stream:
        return None
    pdf = PdfReader(pdf_stream)
    page = pdf.pages[num_page]
    pdf_writer = BrandedFileWriter()
    pdf_writer.add_page(page)
    stream = io.BytesIO()
    pdf_writer.write(stream)
    return stream


def add_banner(
    pdf_stream: io.BytesIO,
    text: str | None = None,
    logo: bool = False,
    thickness: float = SENTINEL,  # type: ignore[assignment]
) -> io.BytesIO:
    from reportlab.lib import colors
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    if thickness is SENTINEL:  # type: ignore[comparison-overlap]
        from reportlab.lib.units import cm

        thickness = 2 * cm

    old_pdf = PdfReader(pdf_stream, strict=False)
    packet = io.BytesIO()
    can = canvas.Canvas(packet)
    with file_open("base/static/img/main_partner-image.png", mode="rb") as f:
        odoo_logo_file = io.BytesIO(f.read())
    odoo_logo = Image.open(odoo_logo_file)
    odoo_color = colors.Color(113 / 255, 75 / 255, 103 / 255, 0.8)

    for p in range(len(old_pdf.pages)):
        page = old_pdf.pages[p]
        width = float(abs(page.mediabox.width))
        height = float(abs(page.mediabox.height))

        can.setPageSize((width, height))
        can.translate(width, height)
        can.rotate(-45)

        path = can.beginPath()
        path.moveTo(-width, -thickness)
        path.lineTo(-width, -2 * thickness)
        path.lineTo(width, -2 * thickness)
        path.lineTo(width, -thickness)
        can.setFillColor(odoo_color)
        can.drawPath(path, fill=1, stroke=False)

        can.setFontSize(10)
        can.setFillColor(colors.white)
        can.drawRightString(0.75 * thickness, -1.45 * thickness, text)
        logo and can.drawImage(
            ImageReader(odoo_logo),
            0.25 * thickness,
            -2.05 * thickness,
            40,
            40,
            mask="auto",
            preserveAspectRatio=True,
        )

        can.showPage()

    can.save()

    watermark_pdf = PdfReader(packet)
    new_pdf = BrandedFileWriter()
    with _debug.perf(
        "pdf.banner_merged", pages=len(old_pdf.pages), logo=logo, text=text
    ):
        for p in range(len(old_pdf.pages)):
            new_pdf.add_page(old_pdf.pages[p])
            new_page = new_pdf.pages[-1]
            if "/Annots" in new_page:
                del new_page["/Annots"]
            new_page.merge_page(watermark_pdf.pages[p])
            new_page.compress_content_streams()

        output = io.BytesIO()
        new_pdf.write(output)

    return output


def reshape_text(text: str) -> str:
    if not text:
        return ""
    maybe_rtl_letter = text.lstrip()[:1] or " "
    maybe_ltr_text = text[1:]
    first_letter_is_rtl = unicodedata.bidirectional(maybe_rtl_letter) in (
        "AL",
        "R",
    )
    no_letter_is_ltr = not any(
        unicodedata.bidirectional(letter) == "L" for letter in maybe_ltr_text
    )
    if first_letter_is_rtl and no_letter_is_ltr:
        text = reshape(text)
        text = text[::-1]

    return text


class OdooPdfFileReader(PdfReader):
    def get_attachments(self) -> Generator[tuple[str, bytes]]:
        if self.is_encrypted:
            self.decrypt("")

        def _traverse_nodes(obj):
            for p in obj.get("/Names", [])[1::2]:
                attachment = p.get_object()
                try:
                    yield (
                        attachment["/F"],
                        attachment["/EF"]["/F"].get_object().get_data(),
                    )
                except KeyError, AttributeError:
                    continue
            for kid in obj.get("/Kids", []):
                key = (
                    (kid.idnum, kid.generation)
                    if isinstance(kid, IndirectObject)
                    else id(kid)
                )
                if key not in visited_nodes:
                    visited_nodes.add(key)
                    yield from _traverse_nodes(kid.get_object())

        try:
            embedded_files = (
                self.trailer["/Root"].get("/Names", {}).get("/EmbeddedFiles", {})
            )
            if not embedded_files:
                _debug.logic("pdf.no_embedded_files", encrypted=self.is_encrypted)
                return
            visited_nodes: set = set()
            yield from _traverse_nodes(embedded_files)
        except Exception as exc:
            _debug.logic("pdf.embedded_files_walk_failed", error=type(exc).__name__)
            return


class OdooPdfFileWriter(BrandedFileWriter):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._reader: PdfReader | None = None
        self.is_pdfa: bool = False

    def format_subtype(self, subtype: str | None) -> str | None:
        if not subtype:
            return subtype

        if REGEX_SUBTYPE_UNFORMATED.match(subtype):
            return "/" + subtype
        if REGEX_SUBTYPE_FORMATED.match(subtype):
            return subtype.replace("#2F", "/")

        _logger.warning(
            "Attempt to add an attachment with the incorrect subtype '%s'. The subtype will be ignored.",
            subtype,
        )
        return ""

    def add_attachment(
        self,
        name: str,
        data: bytes,
        subtype: str | None = None,
        afrelationship: str = "/Data",
    ) -> None:
        valid_afrelationships = {
            "/Source",
            "/Data",
            "/Alternative",
            "/Supplement",
            "/Unspecified",
            "/EncryptedPayload",
            "/FormData",
            "/Schema",
        }
        if afrelationship not in valid_afrelationships:
            _logger.warning(
                "Invalid AFRelationship value '%s', falling back to '/Data'. "
                "Valid values are: %s",
                afrelationship,
                ", ".join(sorted(valid_afrelationships)),
            )
            _debug.logic("pdf.afrelationship_defaulted", given=afrelationship)
            afrelationship = "/Data"

        adapted_subtype = self.format_subtype(subtype)
        _debug.lifecycle(
            "pdf.attachment_added",
            name=name,
            size=len(data),
            subtype=adapted_subtype,
            afrelationship=afrelationship,
            first=not (
                self._root_object.get("/Names")
                and self._root_object["/Names"].get("/EmbeddedFiles")
            ),
        )

        attachment = self._create_attachment_object(
            {
                "filename": name,
                "content": data,
                "subtype": adapted_subtype,
                "afrelationship": afrelationship,
            }
        )
        if self._root_object.get("/Names") and self._root_object["/Names"].get(
            "/EmbeddedFiles"
        ):
            names_array = self._root_object["/Names"]["/EmbeddedFiles"]["/Names"]
            names_array.extend([attachment.get_object()["/F"], attachment])
        else:
            names_array = ArrayObject()
            names_array.extend([attachment.get_object()["/F"], attachment])

            embedded_files_names_dictionary = DictionaryObject()
            embedded_files_names_dictionary.update({NameObject("/Names"): names_array})
            embedded_files_dictionary = DictionaryObject()
            embedded_files_dictionary.update(
                {NameObject("/EmbeddedFiles"): embedded_files_names_dictionary}
            )
            self._root_object.update({NameObject("/Names"): embedded_files_dictionary})

        if self._root_object.get("/AF"):
            attachment_array = self._root_object["/AF"]
            attachment_array.extend([attachment])
        else:
            attachment_array = self._add_object(ArrayObject([attachment]))
            self._root_object.update({NameObject("/AF"): attachment_array})

    def embed_odoo_attachment(
        self,
        attachment: Any,
        subtype: str | None = None,
        afrelationship: str = "/Data",
    ) -> None:
        assert attachment, "embed_odoo_attachment cannot be called without attachment."
        self.add_attachment(
            attachment.name,
            attachment.raw,
            subtype=subtype or attachment.mimetype,
            afrelationship=afrelationship,
        )

    def clone_reader_document_root(self, reader: PdfReader) -> None:
        super().clone_reader_document_root(reader)
        self._reader = reader
        stream = reader.stream
        stream.seek(0)
        header = stream.readline(32).rstrip(b"\r\n")
        if header.startswith(b"%PDF-"):
            self._header = header
        self.is_pdfa = self._declares_pdfa(reader)
        if self._ID is None:
            self._set_id(reader.trailer.get("/ID", None))
        _debug.lifecycle(
            "pdf.reader_cloned",
            pages=len(reader.pages),
            pdfa=self.is_pdfa,
            has_id=self._ID is not None,
        )

    @staticmethod
    def _declares_pdfa(reader: PdfReader) -> bool:
        try:
            xmp = reader.xmp_metadata
        except errors.PyPdfError as exc:
            _debug.logic("pdf.xmp_unreadable", error=type(exc).__name__)
            return False
        if xmp is None:
            return False
        if xmp.rdf_root.getElementsByTagNameNS(PDFA_ID_NAMESPACE, "part"):
            return True
        return any(
            description.getAttributeNodeNS(PDFA_ID_NAMESPACE, "part") is not None
            for description in xmp.rdf_root.getElementsByTagNameNS(
                RDF_NAMESPACE, "Description"
            )
        )

    def _set_id(self, pdf_id: Any) -> None:
        if not pdf_id:
            return
        self._ID = ArrayObject(
            ByteStringObject(part.get_original_bytes())
            if isinstance(part, TextStringObject)
            else part
            for part in pdf_id
        )

    _PDFA_ANNOT_INVISIBLE = 1 << 0
    _PDFA_ANNOT_HIDDEN = 1 << 1
    _PDFA_ANNOT_PRINT = 1 << 2
    _PDFA_ANNOT_NOZOOM = 1 << 3
    _PDFA_ANNOT_NOROTATE = 1 << 4
    _PDFA_ANNOT_NOVIEW = 1 << 5
    _PDFA_ANNOT_TOGGLENOVIEW = 1 << 8

    @classmethod
    def _normalize_annotation_flags(cls, pages: Iterable[Any]) -> None:
        clear = (
            cls._PDFA_ANNOT_HIDDEN
            | cls._PDFA_ANNOT_INVISIBLE
            | cls._PDFA_ANNOT_TOGGLENOVIEW
            | cls._PDFA_ANNOT_NOVIEW
        )
        for page in pages:
            annots = page.get_object().get("/Annots", [])
            if isinstance(annots, IndirectObject):
                annots = annots.get_object()
            for annot_ref in annots:
                annot = annot_ref.get_object()
                if annot.get("/Subtype") == "/Popup":
                    continue
                flags = int(annot.get("/F", 0)) | cls._PDFA_ANNOT_PRINT
                flags &= ~clear
                if annot.get("/Subtype") == "/Text":
                    flags |= cls._PDFA_ANNOT_NOZOOM | cls._PDFA_ANNOT_NOROTATE
                annot[NameObject("/F")] = NumberObject(flags)

    def convert_to_pdfa(self) -> None:
        _debug.pipeline(
            "pdf.convert_to_pdfa", pages=len(self.pages), was_pdfa=self.is_pdfa
        )
        self._header = b"%PDF-1.7"

        assert self._reader is not None
        pdf_id = ByteStringObject(md5(self._reader.stream.getvalue()).digest())
        self._set_id(ArrayObject((pdf_id, pdf_id)))

        with file_open("tools/data/files/sRGB2014.icc", mode="rb") as icc_profile:
            icc_profile_file_data = compress(icc_profile.read())

        icc_profile_stream_obj = DecodedStreamObject()
        icc_profile_stream_obj.set_data(icc_profile_file_data)
        icc_profile_stream_obj.update(
            {
                NameObject("/Filter"): NameObject("/FlateDecode"),
                NameObject("/N"): NumberObject(3),
            }
        )

        icc_profile_obj = self._add_object(icc_profile_stream_obj)

        output_intent_dict_obj = DictionaryObject()
        output_intent_dict_obj.update(
            {
                NameObject("/S"): NameObject("/GTS_PDFA1"),
                NameObject("/OutputConditionIdentifier"): create_string_object("sRGB"),
                NameObject("/DestOutputProfile"): icc_profile_obj,
                NameObject("/Type"): NameObject("/OutputIntent"),
            }
        )

        output_intent_obj = self._add_object(output_intent_dict_obj)
        self._root_object.update(
            {
                NameObject("/OutputIntents"): ArrayObject([output_intent_obj]),
            }
        )

        pages = self._root_object["/Pages"]["/Kids"]

        self._restate_descendant_font_widths(pages)

        self._normalize_annotation_flags(pages)

        outlines = self._root_object.get("/Outlines")
        if outlines is not None:
            outlines.get_object()[NameObject("/Count")] = NumberObject(1)

        mark_info = DictionaryObject({NameObject("/Marked"): BooleanObject(True)})
        self._root_object[NameObject("/MarkInfo")] = mark_info

        struct_tree_root = DictionaryObject(
            {NameObject("/Type"): NameObject("/StructTreeRoot")}
        )
        self._root_object[NameObject("/StructTreeRoot")] = struct_tree_root

        self.add_metadata(
            {
                "/Creator": "Odoo",
                "/Producer": "Odoo",
            }
        )
        self.is_pdfa = True

    def _restate_descendant_font_widths(self, pages) -> None:
        try:
            import fontTools.ttLib
        except ImportError:
            _logger.warning(
                "The fonttools package is not installed. Generated PDF may not be PDF/A compliant."
            )
            return

        fonts = {}
        for page in pages:
            resources = page.get_object().get("/Resources") or {}
            for font in (resources.get("/Font") or {}).values():
                for descendant in font.get_object().get("/DescendantFonts") or ():
                    fonts[descendant.idnum] = descendant.get_object()

        for font in fonts.values():
            descriptor = font.get("/FontDescriptor") or {}
            font_file = descriptor.get("/FontFile2")
            if font_file is None:
                continue
            stream = io.BytesIO(decompress(font_file._data))
            ttfont = fontTools.ttLib.TTFont(stream)
            font_upm = ttfont["head"].unitsPerEm
            if parse_version(fontTools.__version__) < parse_version("4.37.2"):
                glyphs = ttfont.getGlyphSet()._hmtx.metrics
            else:
                glyphs = ttfont.getGlyphSet().hMetrics
            glyph_widths = []
            for key, values in glyphs.items():
                if key[:5] == "glyph":
                    glyph_widths.append(
                        NumberObject(round(1000.0 * values[0] / font_upm))
                    )

            font[NameObject("/W")] = ArrayObject(
                [NumberObject(1), ArrayObject(glyph_widths)]
            )
            stream.close()

    def add_file_metadata(self, metadata_content: bytes) -> None:
        header = b'<?xpacket begin="" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        footer = b'<?xpacket end="w"?>'
        metadata = b"%s%s%s" % (header, metadata_content, footer)
        file_entry = DecodedStreamObject()
        file_entry.set_data(metadata)
        file_entry.update(
            {
                NameObject("/Type"): NameObject("/Metadata"),
                NameObject("/Subtype"): NameObject("/XML"),
            }
        )

        metadata_object = self._add_object(file_entry)
        self._root_object.update({NameObject("/Metadata"): metadata_object})

    def _create_attachment_object(self, attachment: dict[str, Any]) -> Any:
        file_entry = DecodedStreamObject()
        file_entry.set_data(attachment["content"])
        file_entry.update(
            {
                NameObject("/Type"): NameObject("/EmbeddedFile"),
                NameObject("/Params"): DictionaryObject(
                    {
                        NameObject("/CheckSum"): ByteStringObject(
                            md5(attachment["content"]).digest()
                        ),
                        NameObject("/ModDate"): create_string_object(
                            datetime.now(UTC).strftime(DEFAULT_PDF_DATETIME_FORMAT)
                        ),
                        NameObject("/Size"): NumberObject(len(attachment["content"])),
                    }
                ),
            }
        )
        if attachment.get("subtype"):
            file_entry.update(
                {
                    NameObject("/Subtype"): NameObject(attachment["subtype"]),
                }
            )
        file_entry_object = self._add_object(file_entry)
        filename_object = create_string_object(attachment["filename"])
        filespec_object = DictionaryObject(
            {
                NameObject("/AFRelationship"): NameObject(
                    attachment.get("afrelationship", "/Data")
                ),
                NameObject("/Type"): NameObject("/Filespec"),
                NameObject("/F"): filename_object,
                NameObject("/EF"): DictionaryObject(
                    {
                        NameObject("/F"): file_entry_object,
                        NameObject("/UF"): file_entry_object,
                    }
                ),
                NameObject("/UF"): filename_object,
            }
        )
        if attachment.get("description"):
            filespec_object.update(
                {NameObject("/Desc"): create_string_object(attachment["description"])}
            )
        return self._add_object(filespec_object)
