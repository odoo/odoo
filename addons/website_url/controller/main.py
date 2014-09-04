# -*- coding: utf-8 -*-
import werkzeug

from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.http import request

class Website_Url(http.Controller):
    @http.route(['/r/<string:code>'] ,type='http', auth="none", website=True)
    def full_url_redirect(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context
        (ip, country_code) = (request.httprequest.remote_addr, request.session.geoip.get('country_code'))
        return werkzeug.utils.redirect(request.registry['website.alias']
                .get_url_from_code(cr, uid, code, ip, country_code, context=context), 302)
