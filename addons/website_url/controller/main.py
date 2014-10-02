# -*- coding: utf-8 -*-
import werkzeug

from openerp.addons.web import http
from openerp.tools.translate import _
from openerp.http import request

class Website_Url(http.Controller):
    @http.route(['/r/new'], type='json', auth='user', methods=['POST'])
    def create_shorten_url(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        if not 'url' in post or post['url'] == '':
            return {'error':'You have to provide an URL.'}

        tracking_fields = {}
        for key, field in request.registry['crm.tracking.mixin'].tracking_fields():

            if field in post:
                tracking_fields.update({field:post[field]})

        print tracking_fields

        alias = request.registry['website.alias'].create_shorten_url(cr, uid, post['url'], tracking_fields, context=context)

        return alias.to_json()

    @http.route(['/r'] , type='http', auth='user', website=True)
    def shorten_url(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        # return

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
            {'campaigns':campaigns, 'channels':channels, 'sources':sources})

    @http.route(['/r/recent_links'], type='json', auth='user')
    def recent_links(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        return request.registry['website.alias'].recent_links(cr, uid, context=context).to_json()

    @http.route(['/r/archive'], type='json', auth='user', methods=['POST'])
    def archive_link(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        if not 'code' in post:
            return {'error':'No code provided'}

        alias_obj = request.registry['website.alias']
        alias_id = alias_obj.search(cr, uid, [('code', '=', post['code'])])
        alias = alias_obj.browse(cr, uid, alias_id, context=context)

        return alias.archive()


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

    @http.route(['/r/<string:code>'] , type='http', auth="none", website=True)
    def full_url_redirect(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context
        (ip, country_code) = (request.httprequest.remote_addr, request.session.geoip.get('country_code'))

        redirect_url = request.registry['website.alias'].get_url_from_code(cr, uid, code, ip, country_code, context=context)

        if redirect_url is not None:
            return werkzeug.utils.redirect(redirect_url, 301)
        else:
            return werkzeug.utils.redirect('', 301)

    # Routes dedicated to the form selects (possibility to create records on the fly)
    @http.route(['/r/campaigns'], type='json', auth='user')
    def campaigns(self):
        cr, uid, context = request.cr, request.uid, request.context

        campaign_obj = request.registry['crm.tracking.campaign']
        campaign_ids = campaign_obj.search(cr, uid, [], context=context)
        campaigns = campaign_obj.read(cr, uid, campaign_ids, context=context)

        return campaigns

    @http.route(['/r/sources'], type='json', auth='user')
    def sources(self):
        cr, uid, context = request.cr, request.uid, request.context

        source_obj = request.registry['crm.tracking.source']
        source_ids = source_obj.search(cr, uid, [], context=context)
        sources = source_obj.read(cr, uid, source_ids, context=context)

        return sources

    @http.route(['/r/mediums'], type='json', auth='user')
    def mediums(self):
        cr, uid, context = request.cr, request.uid, request.context

        medium_obj = request.registry['crm.tracking.medium']
        medium_ids = medium_obj.search(cr, uid, [], context=context)
        mediums = medium_obj.read(cr, uid, medium_ids, context=context)

        return mediums

    @http.route(['/r/campaigns/new'], type='json', auth='user', methods=['POST'])
    def new_campaign(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        campaign_obj = request.registry['crm.tracking.campaign']
        campaigns = campaign_obj.create(cr, uid, {'name': post['name']}, context=context)

        return campaigns

    @http.route(['/r/mediums/new'], type='json', auth='user', methods=['POST'])
    def new_medium(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        medium_obj = request.registry['crm.tracking.medium']
        mediums = medium_obj.create(cr, uid, {'name': post['name']}, context=context)

        return mediums

    @http.route(['/r/sources/new'], type='json', auth='user', methods=['POST'])
    def new_source(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        source_obj = request.registry['crm.tracking.source']
        sources = source_obj.create(cr, uid, {'name': post['name']}, context=context)

        return sources
