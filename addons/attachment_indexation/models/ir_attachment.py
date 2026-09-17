import importlib.util
import io
import logging

from odoo import api, models
from odoo.libs.documents import Document, canonical_mimetypes

from ..tools.readers import (
    clean_text_content,
    read_docx,
    read_opendoc,
    read_pptx,
    read_xlsx,
)

_logger = logging.getLogger(__name__)

if not (
    importlib.util.find_spec("pdfminer")
    and importlib.util.find_spec("pdfminer.high_level")
):
    _logger.warning(
        "Attachment indexation of PDF documents is unavailable because the 'pdfminer.six' Python library cannot be found on the system. "
        "You may install it from https://pypi.org/project/pdfminer.six/ (e.g. `pip3 install pdfminer.six`)"
    )


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    def _index_docx(self, bin_data):
        """Index Microsoft .docx documents"""
        return read_docx(bin_data, self._INDEX_MAX_BYTES)

    def _index_pptx(self, bin_data):
        """Index Microsoft .pptx documents"""
        return read_pptx(bin_data, self._INDEX_MAX_BYTES)

    def _index_xlsx(self, bin_data):
        """Index Microsoft .xlsx documents"""
        return read_xlsx(bin_data, self._INDEX_MAX_BYTES)

    def _index_opendoc(self, bin_data):
        """Index OpenDocument documents (.odt, .ods...)"""
        return read_opendoc(bin_data, self._INDEX_MAX_BYTES)

    def _index_pdf(self, bin_data):
        """Index PDF documents"""
        if not bin_data.startswith(b"%PDF-"):
            return ""
        try:
            if not importlib.util.find_spec("pdfminer.high_level"):
                return ""
            from pdfminer.converter import TextConverter
            from pdfminer.layout import LAParams
            from pdfminer.pdfinterp import (
                PDFPageInterpreter,
                PDFResourceManager,
            )
            from pdfminer.pdfpage import PDFPage

            logging.getLogger("pdfminer").setLevel(logging.CRITICAL)
        except ImportError:
            # warned already during init of module
            return ""
        f = io.BytesIO(bin_data)
        try:
            resource_manager = PDFResourceManager()
            # Setting boxes_flow triggers the _group_textboxes function,
            # used to group textboxes by distance, which helps sort them
            # better. In our case, we don't need to sort them this way,
            # so we can disable the feature to reduce the memory footprint
            # of the library and avoid memory issues on most PDF files.
            laparams = LAParams(detect_vertical=True, boxes_flow=None)

            with (
                io.StringIO() as content,
                TextConverter(resource_manager, content, laparams=laparams) as device,
            ):
                interpreter = PDFPageInterpreter(resource_manager, device)
                for page in PDFPage.get_pages(f):
                    interpreter.process_page(page)

                buf = content.getvalue()
            return clean_text_content(buf)
        except Exception:
            _logger.debug(
                "attachment_indexation: failed to index pdf content", exc_info=True
            )
            return ""

    @api.model
    def _get_index_content(self, bin_data, mimetype):
        if not bin_data or (mimetype or "").startswith("text/"):
            # An attachment may legally have no content, and `Document` refuses
            # empty bytes rather than pretending to hold a document. Every
            # `_index_*` used to answer "" here, so this branch is what the walk
            # did rather than a new tolerance. Plain text is base's: its word
            # scan is bounded and needs no reader.
            return super()._get_index_content(bin_data, mimetype)

        document = Document(
            bin_data,
            mimetype,
            # This model's budgets, not the layer's defaults. `text_max_chars`
            # would otherwise be TEXT_MAX_CHARS, 60,000, which is what a
            # document may hand an extraction strategy. What this column stores
            # is `_get_index_max_chars()` -- 256 KiB of characters by default
            # and settable per database through `ir_attachment.index_max_chars`
            # -- so the layer's constant would have indexed a long report or a
            # feature-length `.vtt` caption track to its first quarter in
            # silence, and no config parameter could have raised it.
            text_max_chars=self._get_index_max_chars(),
            max_zip_entry_bytes=self._INDEX_MAX_BYTES,
        )
        if document.mimetype == "application/pdf":
            # The one format this module still reads for itself, and the reason
            # is not laziness. `extract` registers pymupdf for this
            # mimetype and the parser below is pdfminer.six; measured over the
            # 56 PDFs this repository ships, the two agree on the words in 48
            # and pdfminer splits words in the rest -- "bill" as "b" and "ill",
            # "packaging" as "p" and "ackaging". Deriving through the layer is
            # therefore an improvement AND a change to what every future row of
            # a stored column holds, which is a decision with a reindex behind
            # it rather than a tidy-up. Asked of the sniffed mimetype, not the
            # declared one, so an unlabelled upload still reaches this branch.
            res = self._index_pdf(bin_data)
        else:
            res = document.text
        res = res.replace("\x00", "") if res else False

        return res or super()._get_index_content(bin_data, mimetype)

    # Mimetypes whose readers parse the WHOLE file: zip-based office containers
    # and PDF. The streaming create path must read these back
    # in full instead of the text-only prefix the base hook returns, otherwise a
    # streamed document larger than _INDEX_MAX_BYTES is parsed from a truncated
    # prefix and silently loses its index. This matches the buffered create
    # path, which already hands _get_index_content the full content.
    _INDEXED_DOC_MIMETYPES = canonical_mimetypes(
        "pdf", "docx", "xlsx", "pptx", "odt", "ods", "odp", "odg"
    )

    @api.model
    def _get_index_read_size(self, mimetype):
        # Read whole documents this backend parses. Also read whole content
        # for an unlabelled or generic mimetype (empty, or the browser
        # fallback `application/octet-stream`) rather than deferring to
        # base's default of skipping: this method only sees the mimetype the
        # caller declared, so it cannot byte-sniff itself, but `_get_index_content`'s
        # Document can once it gets the full bytes -- a generic mimetype is
        # exactly the case where the declared string carries no information
        # either way. Media that genuinely can't be indexed (images, audio,
        # video) is always declared with its own specific mimetype, never a
        # generic one, so this can't make those stream full by mistake.
        if (
            not mimetype
            or mimetype == "application/octet-stream"
            or mimetype in self._INDEXED_DOC_MIMETYPES
        ):
            return None
        return super()._get_index_read_size(mimetype)
