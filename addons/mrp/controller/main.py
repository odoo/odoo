# -*- coding: utf-8 -*-

import base64
import json
import logging

from odoo import http
from odoo.http import request
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


class MrpDocumentRoute(http.Controller):

    def _neuter_mimetype(self, mimetype, user):
        wrong_type = 'ht' in mimetype or 'xml' in mimetype or 'svg' in mimetype
        if wrong_type and not user._is_system():
            return 'text/plain'
        return mimetype

    @http.route('/mrp/upload_attachment', type='http', methods=['POST'], auth="user")
    def upload_document(self, ufile, **kwargs):
        files = request.httprequest.files.getlist('ufile')
        result = {'success': _("All files uploaded")}
        for ufile in files:
            try:
                mimetype = self._neuter_mimetype(ufile.content_type, http.request.env.user)
                request.env['mrp.document'].create({
                    'name': ufile.filename,
                    'res_model': kwargs.get('default_res_model'),
                    'res_id': kwargs.get('default_res_id'),
                    'mimetype': mimetype,
                    'datas': base64.encodebytes(ufile.read()),
                })
            except Exception as e:
                logger.exception("Fail to upload document %s" % ufile.filename)
                result = {'error': str(e)}

        return json.dumps(result)
