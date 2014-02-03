from openerp import http
import simplejson
from openerp.http import request, serialize_exception as _serialize_exception

try:
    import xlwt
except ImportError:
    xlwt = None


class TableExporter(http.Controller):

    @http.route('/web_graph/check_xlwt', type='json', auth='none')
    def check_xlwt(self):
        return xlwt is not None


    @http.route('/web_graph/export_xls', type='http', auth="user")
    def export_xls(self, data, token):
        jdata = simplejson.loads(data)
        model = jdata['test']
        # field = jdata['field']
        # data = jdata['data']
        # id = jdata.get('id', None)
        # filename_field = jdata.get('filename_field', None)
        # context = jdata.get('context', {})
        filecontent='argh'
        print model
        print xlwt

        return request.make_response(filecontent,
            headers=[('Content-Type', 'application/vnd.ms-excel'),
                    ('Content-Disposition', 'attachment; filename=table.xls;')],
            cookies={'fileToken': token})

        # Model = request.session.model(model)
        # fields = [field]
        # if filename_field:
        #     fields.append(filename_field)
        # if data:
        #     res = { field: data }
        # elif id:
        #     res = Model.read([int(id)], fields, context)[0]
        # else:
        #     res = Model.default_get(fields, context)
        # filecontent = base64.b64decode(res.get(field, ''))
        # if not filecontent:
        #     raise ValueError(_("No content found for field '%s' on '%s:%s'") %
        #         (field, model, id))
        # else:
        #     filename = '%s_%s' % (model.replace('.', '_'), id)
        #     if filename_field:
        #         filename = res.get(filename_field, '') or filename
        #     return request.make_response(filecontent,
        #         headers=[('Content-Type', 'application/octet-stream'),
        #                 ('Content-Disposition', content_disposition(filename))],
        #         cookies={'fileToken': token})
