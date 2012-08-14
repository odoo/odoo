# -*- coding: utf-8 -*-
import base64
import simplejson

try:
    import openerp.addons.web.common.http as openerpweb
except ImportError:
    import web.common.http as openerpweb

class ImportController(openerpweb.Controller):
    _cp_path = '/base_import'

    @openerpweb.httprequest
    def set_file(self, req, file, import_id, jsonp='callback'):
        import_id = int(import_id)

        written = req.session.model('base_import.import').write(import_id, {
            'file': base64.b64encode(file.read()),
            'file_name': file.filename,
            'file_type': file.content_type,
        }, req.session.eval_context(req.context))

        return 'window.top.%s(%s)' % (
            jsonp, simplejson.dumps({'result': written}))
