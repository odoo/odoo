# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib
import pathlib

from markupsafe import Markup

from odoo import http
from odoo.http import request

from odoo.modules import get_module_path


BLACKBOX_MODULES = ['pos_blackbox_be']
class GovCertificationController(http.Controller):
    @http.route('/fdm_source', auth='user')
    def handler(self):
        root = pathlib.Path(__file__).parent.parent.parent

        modfiles = [
            p
            for modpath in map(pathlib.Path, map(get_module_path, BLACKBOX_MODULES))
            for p in modpath.glob('**/*')
            if p.is_file()
            if p.suffix in ('.py', '.xml', '.js', '.csv')
            if '/tests/' not in str(p)
        ]
        modfiles.sort()

        files_data = []
        main_hash = hashlib.sha1()
        for p in modfiles:
            content = p.read_bytes()
            content_hash = hashlib.sha1(content).hexdigest()
            files_data.append({
                'name': p.relative_to(root),
                'size_in_bytes': p.stat().st_size,
                'contents': Markup(content.decode()),
                'hash': content_hash
            })
            main_hash.update(content_hash.encode())

        data = {
            'files': files_data,
            'main_hash': main_hash.hexdigest(),
        }

        return request.render('pos_blackbox_be.fdm_source', data, mimetype='text/plain')

    @http.route("/journal_file/<string:serial>", auth="user")
    def journal_file(self, serial, **kw):
        """ Give the journal file report for a specific blackbox
        serial: e.g. BODO001bd6034a
        """
        logs = request.env["pos_blackbox_be.log"].search([
            ("action", "=", "create"),
            ("description", "ilike", serial),
        ], order='id')

        data = {
            'pos_id': serial,
            'logs': logs,
        }

        return request.render("pos_blackbox_be.journal_file", data, mimetype="text/plain")
