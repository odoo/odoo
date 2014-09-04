# -*- coding: utf-8 -*-
import datetime
import werkzeug

from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.http import request

class Website_Url(http.Controller):
    @http.route(['/r/<string:code>'] ,type='http', auth="none", website=True)
    def full_url_redirect(self, code, **post):
        record = request.env['website.alias'].sudo().search_read([('code', '=', code)], ['url'])
        website_alias_click = request.env['website.alias.click']
        ip = request.httprequest.remote_addr
        again = website_alias_click.sudo().search_read([('alias_id', '=', record[0]['id']), ('ip', '=', ip)], ['id'])
        rec = record and record[0] or False
        if rec:
            if not again:
                country_id = request.env['res.country'].sudo().search([('code','=',request.session.geoip.get('country_code'))])
                vals = {
                    'alias_id':rec.get('id'),
                    'create_date':datetime.datetime.now().date(),
                    'ip':ip,
                    'country_id': country_id and country_id[0] or False,
                }
                website_alias_click.sudo().create(vals)
            return werkzeug.utils.redirect(rec.get('url'))
