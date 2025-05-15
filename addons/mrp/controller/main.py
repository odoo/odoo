# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
import logging

from odoo import http
from odoo.http import request

logger = logging.getLogger(__name__)


class MrpDocumentRoute(http.Controller):

    @http.route('/mrp/upload_attachment', type='http', methods=['POST'], auth="user")
    def upload_document(self, ufile, **kwargs):
        res_model = kwargs.get("res_model")
        res_id = kwargs.get("res_id")
        record = request.env[res_model].browse(int(res_id)).exists()
        if not record or not record.browse().has_access('write'):
            return

        files = request.httprequest.files.getlist('ufile')
        result = {'success': self.env._("All files uploaded")}
        for ufile in files:
            try:
                mimetype = ufile.content_type
                request.env['mrp.document'].with_context(
                    disable_product_documents_creation=True
                ).create({
                    'name': ufile.filename,
                    'res_model': res_model,
                    'res_id': int(res_id),
                    'mimetype': mimetype,
                    'datas': base64.encodebytes(ufile.read()),
                })
            except Exception as e:
                logger.exception("Fail to upload document %s", ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
