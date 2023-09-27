# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http
from odoo.http import request
from odoo.tools import misc


class ImportController(http.Controller):

    @http.route('/base_import/set_file', methods=['POST'])
    # pylint: disable=redefined-builtin
    def set_file(self, id):
        file = request.httprequest.files.getlist('ufile')[0]
        file_data = file.read()
        if(len(file_data) > request.env['ir.http'].session_info()['max_file_upload_size']):
            return json.dumps({
                'import_size_exceeded': True,
                'result': False,
            })

        written = request.env['base_import.import'].browse(int(id)).write({
            'file': file_data,
            'file_name': file.filename,
            'file_type': file.content_type,
        })

        return json.dumps({'result': written})
