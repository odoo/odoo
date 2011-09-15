import urlparse
import cherrypy

from openobject import rpc
from openobject.tools import expose, ast

import openerp.controllers



class ShareWizardController(openerp.controllers.SecuredController):
    _cp_path = "/share"

    @expose()
    def index(self, domain, context, view_id, search_domain='[]', action_id=None):
        context = ast.literal_eval(context)

        if not action_id:
            # This should not be needed anymore, but just in case users are
            # running the module with an older version of the web client...

            # to remove soon-ish
            action_id = rpc.RPCProxy('ir.actions.act_window').search(
                [('view_id','=',int(view_id))], context=context)
            if not action_id: return ""

            action_id = action_id[0]

        domain = ast.literal_eval(domain)
        domain.extend(ast.literal_eval(search_domain))

        scheme, netloc, _, _, _ = urlparse.urlsplit(cherrypy.request.base)
        share_root_url = urlparse.urlunsplit((
            scheme, netloc, '/openerp/login',
            'db=%(dbname)s&user=%(login)s&password=%(password)s', ''))

        context.update(
            #active_ids=share_wiz_id,
            #active_id=share_wiz_id[0],
            _terp_view_name='Share Wizard',
            share_root_url=share_root_url)
        Share = rpc.RPCProxy('share.wizard')
        sharing_view_id = Share.create({
            'domain': str(domain),
            'action_id': action_id and int(action_id)
        }, context)
        return openerp.controllers.actions.execute(
            Share.go_step_1([sharing_view_id], context),
            ids=[sharing_view_id], context=context)
