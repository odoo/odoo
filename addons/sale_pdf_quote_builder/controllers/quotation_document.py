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
                doc = request.env['quotation.document'].create({
                    'name': ufile.filename,
                    'mimetype': mimetype,
                    'raw': ufile.read(),
                    **additional_vals,
                })
                # pypdf will also catch malformed document
                utils._ensure_document_not_encrypted(base64.b64decode(doc.datas))
            except Exception as e:
                logger.exception("Failed to upload document %s", ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
