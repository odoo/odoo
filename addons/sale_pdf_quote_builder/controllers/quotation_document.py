# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import json
import logging

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route
from odoo.tools import pdf

logger = logging.getLogger(__name__)


class QuotationDocumentController(Controller):

    @route(
        '/sale_pdf_quote_builder/quotation_document/upload',
        type='http',
        methods=['POST'],
        auth='user',
    )
    def upload_document(self, ufile, sale_order_template_id=False, allowed_company_ids=False):
        if allowed_company_ids:
            request.update_context(allowed_company_ids=json.loads(allowed_company_ids))
        sale_order_template = request.env['sale.order.template'].browse(
            int(sale_order_template_id)
        )
        if sale_order_template:
            sale_order_template.check_access('write')
            additional_vals = {
                'company_id': sale_order_template.company_id.id,
                'quotation_template_ids': sale_order_template.ids,
            }
        else:
            additional_vals = {
                'company_id': request.env.company.id,
            }
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = ufile.content_type
                pdf_bytes = ufile.read()
                # pypdf will also catch malformed document
                if pdf.PdfFileReader(io.BytesIO(pdf_bytes), strict=False).isEncrypted:
                    raise ValidationError(_(  # noqa: TRY301
                        "It seems that we're not able to process this pdf inside a quotation. It is either"
                        " encrypted, or encoded in a format we do not support."
                    ))
                request.env['quotation.document'].create({
                    'name': ufile.filename,
                    'mimetype': mimetype,
                    'raw': pdf_bytes,
                    **additional_vals,
                })
            except Exception as e:
                logger.exception("Failed to upload document %s", ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
