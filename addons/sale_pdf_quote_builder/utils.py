import base64
import io

from odoo import _
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import pdf

_debug = DebugLog(__name__)


def _check_document_not_encrypted(document):
    document_is_invalid = False
    try:
        document_is_invalid = pdf.PdfReader(
            io.BytesIO(document), strict=False
        ).is_encrypted
    except pdf.DependencyError, pdf.PdfReadError:
        document_is_invalid = True
    if document_is_invalid:
        _debug.logic("pdf_document_encrypted")
        raise ValidationError(
            _(
                "It seems that we're not able to process this pdf inside a quotation. It is either"
                " encrypted, or encoded in a format we do not support."
            )
        )


def _get_form_fields_from_pdf(pdf_data):
    pdf_bytes = base64.b64decode(pdf_data)
    _check_document_not_encrypted(pdf_bytes)

    reader = pdf.PdfReader(io.BytesIO(pdf_bytes), strict=False)

    return set(reader.get_form_text_fields() or {})
