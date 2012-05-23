import werkzeug

from openerp.addons.web.common import http as oeweb
#from openerp.addons.web.controllers.main import db_list

def db_list(r):
    return ['trunk_anonymous']

class PublicController(oeweb.Controller):
    _cp_path = '/public'

    @oeweb.httprequest
    def index(self, req):
        dbs = db_list(req)
        if len(dbs) == 1:
            url = '/web/webclient/login?db=%s&login=anonymous&key=anonymous' % (dbs[0],)
        else:
            url = '/'
        return werkzeug.utils.redirect(url)
