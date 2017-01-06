# -*- coding: utf-8 -*-
import cgi
import simplejson

from openerp.http import Controller, route

class ImportController(Controller):
    @route('/base_import/set_file')
    def set_file(self, req, file, import_id, jsonp='callback'):
        import_id = int(import_id)

        written = req.session.model('base_import.import').write(import_id, {
            'file': file.read(),
            'file_name': file.filename,
            'file_type': file.content_type,
        }, req.context)

        return 'window.top.%s(%s)' % (
            cgi.escape(jsonp), simplejson.dumps({'result': written}))
