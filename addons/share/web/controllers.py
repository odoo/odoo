import urlparse

import cherrypy

from openobject.tools import expose, ast
import openerp.controllers
from openerp.controllers import actions
from openerp.utils import rpc, TinyDict

class Piratepad(openerp.controllers.SecuredController):
    _cp_path = "/share"
    
    @expose()
    def index(self, **kw):
        domain = ast.literal_eval(kw['domain'])
        search_domain = ast.literal_eval(kw['search_domain'])
        filter_domain = ast.literal_eval(kw['filter_domain'])
        
        context = ast.literal_eval(kw['context'])
        view_name = context.get('_terp_view_name')
        
        domain.extend(search_domain)
        
        action_id = rpc.RPCProxy('ir.actions.actions').search([('name','=',view_name)], 0, 0, 0, context)
        if action_id:
            action_id = action_id[0]
        
        model =  'share.wizard'
        proxy = rpc.RPCProxy(model)
        
        share_wiz_id = rpc.RPCProxy('ir.ui.menu').search([('name','=', 'Share Wizard')])
        context.update({'active_ids': share_wiz_id, 'active_id': share_wiz_id[0], '_terp_view_name': 'Share Wizard'})
        data = {'domain': str(domain), 'action_id':action_id}
        id = proxy.create(data, context)
        res = rpc.session.execute('object', 'execute', model, 'go_step_1', [id], context)
        return actions.execute(res, ids=[id])
    
