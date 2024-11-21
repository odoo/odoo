# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging

from odoo import _
from odoo.http import Controller, request, route

from odoo.addons.sale_pdf_quote_builder import utils

logger = logging.getLogger(__name__)


class QuotationDocumentController(Controller):

    @route(
        '/sale_pdf_quote_builder/quotation_document/upload',
        type='http',
        methods=['POST'],
        auth='user',
    )
    def upload_document(self, ufile, sale_order_template_id=False):
        sale_order_template_id = request.env['sale.order.template'].browse(
            int(sale_order_template_id)
        )
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = ufile.content_type
                doc = request.env['quotation.document'].create({
                    'name': ufile.filename,
                    'mimetype': mimetype,
                    'raw': ufile.read(),
                    'quotation_template_ids': sale_order_template_id,
                })
                # pypdf will also catch malformed document
                utils._ensure_document_not_encrypted(base64.b64decode(doc.datas))
            except Exception as e:
                logger.exception("Failed to upload document %s", ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
