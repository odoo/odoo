import logging
import json

from werkzeug.datastructures import FileStorage

from odoo import http
from odoo.http import request, content_disposition
from odoo.addons.spreadsheet.controllers.main import SpreadsheetController


logger = logging.getLogger(__name__)


class SpreadsheetEditionController(SpreadsheetController):


    @http.route('/spreadsheet/xlsx', type='http', auth="user", methods=["POST"])
    def get_xlsx_file(self, zip_name, files, **kw):
        if not request.env.user.has_group('base.group_allow_export'):
            raise request.not_found()
        if datasources := kw.get("datasources"):
            self._log_spreadsheet_export("download", request.env.uid, json.load(datasources))

        files = json.load(files) if isinstance(files, FileStorage) else json.loads(files)

        content = request.env['spreadsheet.mixin']._zip_xslx_files(files)
        headers = [
            ('Content-Length', len(content)),
            ('Content-Type', 'application/vnd.ms-excel'),
            ('X-Content-Type-Options', 'nosniff'),
            ('Content-Disposition', content_disposition(zip_name))
        ]

        response = request.make_response(content, headers)
        return response
