import urlparse

from openobject.tools import expose, ast
from openerp.controllers import actions
from openerp.utils import rpc

import openerp.controllers
import cherrypy



class ShareWizardController(openerp.controllers.SecuredController):
    _cp_path = "/share"

    @expose()
    def index(self, domain, search_domain, context, name, view_type):
        context = ast.literal_eval(context)
        view_name = context.get('_terp_view_name') or name
        if not view_name: return

        action_id = rpc.RPCProxy('ir.actions.actions').search(
            [('name','=',view_name)], 0, 0, 0, context)
        
        if not action_id:
            action_id = rpc.RPCProxy('ir.actions.act_window').search([('view_type','=', view_type),('name','=',view_name)], 0, 0, 0, context)
            
        if not action_id: return

        domain = ast.literal_eval(domain)
        search_domain = ast.literal_eval(search_domain)
        domain.extend(search_domain)

        action_id = action_id[0]
        share_model =  'share.wizard'

        scheme, netloc, _, _, _ = urlparse.urlsplit(cherrypy.request.base)
        share_root_url = urlparse.urlunsplit((
            scheme, netloc, '/openerp/login',
            'db=%(dbname)s&user=%(login)s&password=%(password)s', ''))

        share_wiz_id = rpc.RPCProxy('ir.ui.menu').search(
            [('name','=', 'Share Wizard')])
        context.update(
            active_ids=share_wiz_id,
            active_id=share_wiz_id[0],
            _terp_view_name='Share Wizard',
            share_root_url=share_root_url)
        sharing_view_id = rpc.RPCProxy(share_model).create({
            'domain': str(domain),
            'action_id':action_id
        }, context)
        return actions.execute(
            rpc.session.execute('object', 'execute', share_model, 'go_step_1',
                                [sharing_view_id], context),
            ids=[sharing_view_id], context=context)
