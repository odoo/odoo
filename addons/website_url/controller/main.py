# -*- coding: utf-8 -*-
import werkzeug

from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.http import request

class Website_Url(http.Controller):
    @http.route(['/r/<string:code>'] , type='http', auth="none", website=True)
    def full_url_redirect(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context
        (ip, country_code) = (request.httprequest.remote_addr, request.session.geoip.get('country_code'))
        return werkzeug.utils.redirect(request.registry['website.alias']
                .get_url_from_code(cr, uid, code, ip, country_code, context=context), 302)

    @http.route(['/r/new'], type='json', auth='user', methods=['POST'], website=True)
    def create_shorten_url(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        shorten_url = request.registry['website.alias'].create_shorten_url(cr, uid, post['url'], context=context)
        return shorten_url

    @http.route(['/r'] , type='http', auth="none", website=True)
    def shorten_url(self, **post):
        return request.website.render("website_url.page_shorten_url", {'k':'x'})

    """@http.route(['/r/<string:code>+'] , type='http', auth="user", website=True)
    def statistics_shorten_url(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context
        # JSH Todo: Find way to redirect user. to statistics of the
        # perticular url code
        action_id = request.registry['ir.actions.act_window'].for_xml_id(cr, uid, 'website_url', 'action_website_alias_stats', context=context)['id']
        return werkzeug.utils.redirect("/web#view_type=graph&model=website.alias.click&action=%d" % (action_id), 302)"""
    @http.route(['/r/<string:code>+'] , type='http', auth="user", website=True)
    def statistics_shorten_url(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context
        return request.website.render("website_url.graphs", {})
    @http.route(['/r/<string:code>/chart'], type="json", auth="user", website=True)
    def chart_data(self, code):
        cr, uid, context = request.cr, request.uid, request.context
        Alias = request.registry['website.alias']
        Alias_clicks = request.registry['website.alias.click']

        alias_id = Alias.search_read([('code', '=', code)], ['id'])
        #for data in Alias_clicks.sudo().search_read([('alias_id', '=', alias_id)], ['alias_id', 'click_date', 'country_id']):
            
        return 

