# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools import pdf

try:
    from PyPDF2.errors import PdfReadError
except ImportError:
    from PyPDF2.utils import PdfReadError


def _ensure_document_not_encrypted(document):
    try:
        pdf_reader = pdf.PdfFileReader(io.BytesIO(document), strict=False)
    except PdfReadError as e:
        raise ValidationError(_('Error when reading the pdf file: %s', e))
    if pdf_reader.isEncrypted:
        raise ValidationError(_(
            "It seems that we're not able to process this pdf inside a quotation. It is either "
            "encrypted, or encoded in a format we do not support."
        ))
