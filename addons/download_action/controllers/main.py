# -*- coding: utf-8 -*-

import logging
import mimetypes

try:
    import simplejson as json
except ImportError:
    import json

from openerp import http
from openerp.http import request
from openerp.addons.web.controllers.main import (
    serialize_exception,
    content_disposition
)

_logger = logging.getLogger(__name__)


class DownloadController(http.Controller):

    @http.route('/download', type='http', auth='user')
    @serialize_exception
    def download(self, data, token):
        cr, uid, context = request.cr, request.uid, request.context
        model = request.registry['ir.actions.download']
        params = json.loads(data)
        _logger.debug('Starting download, POST data: %s', params)

        download_id = params.get('download_id')
        file_content, filename, mimetype = model._get_download(
            cr, uid, download_id, context=context)
        if file_content:
            content_type = (mimetype or mimetypes.guess_type(filename)[0] or
                            'application/octet-stream')
            return request.make_response(
                file_content,
                headers=[
                    ('Content-Type', content_type),
                    ('Content-Disposition', content_disposition(filename))
                ],
                cookies={'fileToken': token})

        _logger.warning('File not found: %s' % params)
        return request.not_found()
