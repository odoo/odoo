from openobject.tools import expose
from openerp.controllers import form
from openerp.utils import rpc, TinyDict
import cherrypy

class Form(form.Form):
    _cp_path = "/piratepad/form"

    @expose('json', methods=('POST',))
    def save(self, pad_name):
        params, data = TinyDict.split(cherrypy.session['params'])
        ctx = dict(rpc.session.context,
                   default_res_model=params.model, default_res_id=params.id,
                   active_id=False, active_ids=[])

        pad_link = "http://piratepad.net/"+'-'.join(pad_name.split())
        attachment_id = rpc.RPCProxy('ir.attachment').create({
            'name': pad_name,
            'url': pad_link,
            }, ctx)
        return {'id': attachment_id, 'name': pad_name, 'url': pad_link}
