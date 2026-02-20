# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import traceback
from http import HTTPStatus

from odoo.http import Controller, request, route

logger = logging.getLogger(__name__)


class MrpDocumentRoute(Controller):

    @route('/mrp/document/upload', type='http', methods=['POST'], auth="user")
    def upload_document(self, ufile, res_model, res_id):
        record = request.env[res_model].browse(int(res_id)).exists()
        if not record or not record.browse().has_access('write'):
            return

        files = request.httprequest.files.getlist('ufile')
        for ufile in files:
            try:
                mimetype = ufile.content_type
                request.env['mrp.document'].with_context(
                    disable_product_documents_creation=True
                ).create({
                    'name': ufile.filename,
                    'res_model': record._name,
                    'res_id': record.id,
                    'company_id': record.company_id.id,
                    'mimetype': mimetype,
                    'raw': ufile.read(),
                })
            except Exception as e:
                request.env.cr.rollback()
                logger.exception("Failed to upload document %s", ufile.filename)
                return request.make_json_response(
                    {'error': traceback.format_exception(e, limit=0)[0].rstrip()},
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
        return request.make_json_response({'success': self.env._("All files uploaded")})