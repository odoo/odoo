# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import traceback
from http import HTTPStatus

from odoo import _
from odoo.exceptions import UserError
from odoo.http import Controller, request, route

logger = logging.getLogger(__name__)


class QuotationDocumentController(Controller):

    @route(
        '/sale_pdf_quote_builder/quotation_document/upload',
        type='http',
        methods=['POST'],
        auth='user',
    )
    def upload_document(self, ufile, sale_order_template_id=False):
        # TODO: add `allowed_company_ids` as method param in master
        if allowed_company_ids := request.params.get('allowed_company_ids'):
            request.update_context(allowed_company_ids=json.loads(allowed_company_ids))
        sale_order_template = request.env['sale.order.template'].browse(
            int(sale_order_template_id)
        )
        company = sale_order_template.company_id if sale_order_template else request.env.company
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = ufile.content_type
                request.env['quotation.document'].create({
                    'name': ufile.filename,
                    'mimetype': mimetype,
                    'raw': ufile.read(),
                    'quotation_template_ids': sale_order_template.ids,
                    'company_id': company.id,
                }).flush_recordset()
            except UserError as e:
                request.env.cr.rollback()
                return request.make_json_response(
                    {'error': e},
                    status=HTTPStatus.BAD_REQUEST,  # TODO saas-18.3 and up: e.http_status
                )
            except Exception as e:
                request.env.cr.rollback()
                logger.exception("Failed to upload document %s", ufile.filename)
                return request.make_json_response(
                    {'error': traceback.format_exception(e, limit=0)[0].rstrip()},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        return request.make_json_response(result)
