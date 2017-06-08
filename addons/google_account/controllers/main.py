import simplejson
import urllib
import openerp
from openerp import http
from openerp.http import local_redirect, request
import openerp.addons.web.controllers.main as webmain
from openerp.addons.web.http import SessionExpiredException
from werkzeug.exceptions import BadRequest
import werkzeug.utils

class google_auth(http.Controller):
    
    @http.route('/google_account/authentication', type='http', auth="none")
    def oauth2callback(self, **kw):
        """ This route/function is called by Google when user Accept/Refuse the consent of Google """
        
        state = simplejson.loads(kw['state'])
        dbname = state.get('d')
        service = state.get('s')
        url_return = state.get('f')
        
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            if kw.get('code',False):
                registry.get('google.%s' % service).set_all_tokens(cr,request.session.uid,kw['code'])
                return local_redirect(url_return, code=302)
            elif kw.get('error'):
                return local_redirect("%s%s%s" % (url_return, "?error=", kw.get('error')), code=302)
            else:
                return local_redirect("%s%s" % (url_return, "?error=Unknown_error"), code=302)
