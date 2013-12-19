import simplejson
import urllib
import openerp
import openerp.addons.web.http as http
from openerp.addons.web.http import request
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
        url_return = state.get('from')
        
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        with registry.cursor() as cr:
            if kw.get('code'):
                registry.get('google.%s' % service).set_all_tokens(cr,request.session.uid,kw['code'])
                return werkzeug.utils.redirect(url_return)
            
            #TODO - Display error at customer if url contains ?Error=
            elif kw.get('error'):
                return werkzeug.utils.redirect("%s%s%s" % (url_return ,"?Error=" , kw.get('error')))
            else:
                return werkzeug.utils.redirect("%s%s%s" % (url_return ,"?Error=Unknown_error"))

        
