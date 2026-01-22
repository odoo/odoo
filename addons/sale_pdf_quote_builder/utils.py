# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools import pdf


def _ensure_document_not_encrypted(document):
    document_is_invalid = False
    try:
        document_is_invalid = pdf.PdfFileReader(io.BytesIO(document), strict=False).isEncrypted
    except (pdf.DependencyError, pdf.PdfReadError):
        document_is_invalid = True
    if document_is_invalid:
        raise ValidationError(_(
            "It seems that we're not able to process this pdf inside a quotation. It is either"
            " encrypted, or encoded in a format we do not support."
        ))


def _get_form_fields_from_pdf(pdf_data):
    """Get the form text fields present in the pdf file.

    :param binary pdf_data: the pdf from where we should extract the new form fields that might
                            need to be mapped.
    :return: set of form fields that are in the pdf.
    :rtype: set
    """
    pdf_bytes = base64.b64decode(pdf_data)
    _ensure_document_not_encrypted(pdf_bytes)

    reader = pdf.PdfFileReader(io.BytesIO(pdf_bytes), strict=False)

    return set(reader.getFormTextFields() or {})
