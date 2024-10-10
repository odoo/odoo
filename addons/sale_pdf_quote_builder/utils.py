# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools import pdf

try:
    from PyPDF2.errors import PdfReadError
except ImportError:
    from PyPDF2.utils import PdfReadError


def _ensure_document_not_encrypted(document):
    if pdf.PdfFileReader(io.BytesIO(document), strict=False).isEncrypted:
        raise ValidationError(_(
            "It seems that we're not able to process this pdf inside a quotation. It is either"
            " encrypted, or encoded in a format we do not support."
        ))


def _get_form_fields_from_pdf(pdf_data):
    """ Get the form fields present in the pdf file.

    :param binary pdf_data: the pdf from where we should extract the new form fields that might
                            need to be mapped.
    :return: set of form fields that are in the pdf.
    :rtype: set
    """
    try:
        reader = pdf.PdfFileReader(io.BytesIO(base64.b64decode(pdf_data)))
    except PdfReadError as e:
        raise ValidationError(_("Unable to read the File Content or %s.", e))

    return set(reader.getFields() or '')
