from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import serialize_exception,content_disposition
import base64

class BinaryCDFIInvoice(http.Controller):
    
    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(self,model,field,id,filename=None, **kw):
        """ Download link for files stored as binary fields.
         :param str model: name of the model to fetch the binary from
         :param str field: binary field
         :param str id: id of the record from which to fetch the binary
         :param str filename: field holding the file's name, if any
         :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = request.registry[model]
        cr, uid, context = request.cr, request.uid, request.context
        fields = [field]
        res = Model.read(cr, uid, [int(id)], fields, context)[0]
        filecontent = base64.b64decode(res.get(field) or '')
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
        return request.make_response(filecontent,
                            [('Content-Type', 'application/pdf'),
                             ('Content-Disposition', content_disposition(filename))])