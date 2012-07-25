import simplejson
import urllib2
import werkzeug

from openerp.addons.web.common import http as oeweb

class ResetPassword(oeweb.Controller):
    _cp_path = '/reset_password'

    @oeweb.httprequest
    def index(self, req, db, token):
        req.session.authenticate(db, 'anonymous', 'anonymous', {})
        url = '/web/webclient/home#client_action=reset_password&token=%s' % (token,)
        redirect = werkzeug.utils.redirect(url)
        cookie_val = urllib2.quote(simplejson.dumps(req.session_id))
        redirect.set_cookie('instance0|session_id', cookie_val)
        return redirect
