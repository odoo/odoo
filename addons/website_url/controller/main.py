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

        redirect_url = request.registry['website.alias'].get_url_from_code(cr, uid, code, ip, country_code, context=context)

        if redirect_url is not None:
            return werkzeug.utils.redirect(redirect_url, 301)
        else:
            return werkzeug.utils.redirect('', 301)

    @http.route(['/r/new'], type='json', auth='user', methods=['POST'], website=True)
    def create_shorten_url(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        crm_tracking_mixin = request.registry['crm.tracking.mixin']

        tracking_fields = {}
        for key, field in crm_tracking_mixin.tracking_fields():

            if field in post:
                tracking_fields.update({field:post[field]})

        alias = request.registry['website.alias'].create_shorten_url(cr, uid, post['url'], tracking_fields, context=context)

        return alias.to_json()

    @http.route(['/r'] , type='http', auth='user', website=True)
    def shorten_url(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        alias_obj = request.registry['website.alias']
        alias_ids = alias_obj.search(cr, uid, [], order="write_date DESC", context=context)
        alias = alias_obj.browse(cr, uid, alias_ids, context=context)

        campaign_obj = request.registry['crm.tracking.campaign']
        campaign_ids = campaign_obj.search(cr, uid, [], context=context)
        campaigns = campaign_obj.browse(cr, uid, campaign_ids, context=context)

        channel_obj = request.registry['crm.tracking.medium']
        channel_ids = channel_obj.search(cr, uid, [], context=context)
        channels = channel_obj.browse(cr, uid, channel_ids, context=context)

        source_obj = request.registry['crm.tracking.source']
        source_ids = source_obj.search(cr, uid, [], context=context)
        sources = source_obj.browse(cr, uid, source_ids, context=context)

        return request.website.render("website_url.page_shorten_url", 
            {'campaigns':campaigns, 'channels':channels, 'sources':sources, 'alias':alias})

    @http.route(['/r/recent_links'], type='json', auth='user', website=True)
    def recent_links(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        return request.registry['website.alias'].recent_links(cr, uid, context=context).to_json()

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

