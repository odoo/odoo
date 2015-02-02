# -*- coding: utf-8 -*-
import simplejson
import zipfile

from openerp.http import Controller, route

class ImportController(Controller):
    @route('/base_import/set_file')
    def set_file(self, req, file, import_id, jsonp='callback'):
        import_id = int(import_id)
        if file.filename[-3:] == "ods":
            file_content = zipfile.ZipFile(file).read('content.xml')
        else:
            file_content = file.read()

        written = req.session.model('base_import.import').write(import_id, {
            'file': file_content,
            'file_name': file.filename,
            'file_type': file.content_type,
        }, req.context)
        return 'window.top.%s(%s)' % (
            jsonp, simplejson.dumps({'result': written}))
