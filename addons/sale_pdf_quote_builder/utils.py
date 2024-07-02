# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io

from odoo import _
from odoo.exceptions import ValidationError
from odoo.tools import pdf


def _ensure_document_not_encrypted(document):
    if pdf.PdfFileReader(io.BytesIO(document), strict=False).isEncrypted:
        raise ValidationError(_(
            "It seems that we're not able to process this pdf inside a quotation. It is either"
            " encrypted, or encoded in a format we do not support."
        ))


def _get_valid_form_fields(pdf_data):
    """ Update the restricted paths set to add restricted paths present in the pdf file.

    :param set restricted_paths: paths that are not whitelisted.
    :param binary pdf_data: the pdf from where we should extract the new form fields that still
                            needs to be whitelisted.
    :param recordset record: empty recorset of either sale.order or sale.order.line from where the
                             paths extracted from the PDF data should begin.
    :return: updated set of paths that are not whitelisted.
    :rtype: dict(models:[fields])
    """
    reader = pdf.PdfFileReader(io.BytesIO(base64.b64decode(pdf_data)))

    return set(reader.getFields() or '')
