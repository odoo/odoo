# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import _
from odoo.http import request, route, Controller

logger = logging.getLogger(__name__)


class ProductDocumentController(Controller):

    @route('/product/document/upload', type='http', methods=['POST'], auth='user')
    def upload_document(self, ufile, res_model, res_id, **kwargs):
        if not self.is_model_valid(res_model):
            return

        record = request.env[res_model].browse(int(res_id)).exists()

        if not record or not record.browse().has_access('write'):
            return

        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = ufile.content_type
                request.env['product.document'].create({
                    'name': ufile.filename,
                    'res_model': record._name,
                    'res_id': record.id,
                    'company_id': record.company_id.id,
                    'mimetype': mimetype,
                    'raw': ufile.read(),
                    **self.get_additional_create_params(**kwargs)
                })
            except Exception as e:
                logger.exception("Failed to upload document %s", ufile.filename)
                result = {'error': str(e)}
        return json.dumps(result)

    # mrp hook
    def get_additional_create_params(self, **kwargs):
        return {}

    # eco hook
    def is_model_valid(self, res_model):
        return res_model in ('product.product', 'product.template')
