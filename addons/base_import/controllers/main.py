# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import http, _
from odoo.http import request
from odoo.tools import misc
from odoo.exceptions import UserError

class ImportController(http.Controller):

    @http.route('/base_import/set_file', methods=['POST'])
    def set_file(self, file, import_id, jsonp='callback'):
        import_id = int(import_id)

        try:
            written = request.env['base_import.import'].browse(import_id).write({
                'file': file.read(),
                'file_name': file.filename,
                'file_type': file.content_type,
            })
        except UserError as e:
            title = _("User Error")
            content = _(".xlsx are not allowed unless you have administrator rights. You can convert your file in .xls or .csv to avoid this issue.")
            return """odoo.define(function (require) {
                var web_client = require('web.web_client');
                web_client.do_warn("%s", "%s", true);
                });""" % (title, content)

        return 'window.top.%s(%s)' % (misc.html_escape(jsonp), json.dumps({'result': written}))
