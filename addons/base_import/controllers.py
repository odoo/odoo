# -*- coding: utf-8 -*-
import simplejson

import openerp

class ImportController(openerp.addons.web.http.Controller):
    _cp_path = '/base_import'

    @openerp.addons.web.http.httprequest
    def set_file(self, req, file, import_id, jsonp='callback'):
        import_id = int(import_id)

        written = req.session.model('base_import.import').write(import_id, {
            'file': file.read(),
            'file_name': file.filename,
            'file_type': file.content_type,
        }, req.context)

        return 'window.top.%s(%s)' % (
            jsonp, simplejson.dumps({'result': written}))
