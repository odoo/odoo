# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging

from odoo import _
from odoo.http import request, route, Controller

logger = logging.getLogger(__name__)


class SalePdfHeaderFooterController(Controller):

    @route(
        '/sale_pdf_quote_builder/header_footer/upload', type='http', methods=['POST'], auth='user'
    )
    def upload_document(self):
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = ufile.content_type
                request.env['sale.pdf.header.footer'].create({
                    'name': ufile.filename, 'mimetype': mimetype, 'raw': ufile.read()
                })
            except Exception as e:
                logger.exception("Failed to upload document %s", ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
