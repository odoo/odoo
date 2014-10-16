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
            return {'error':'empty_url'}

        # Get trackings fields returned by the users
        tracking_fields = {}
        for key, field in request.registry['crm.tracking.mixin'].tracking_fields():
            if field in post:
                tracking_fields.update({field:post[field]})

        alias = request.registry['website.alias'].create_shorten_url(cr, uid, post['url'], tracking_fields, context=context)

        return alias.to_json()

    @http.route(['/r'] , type='http', auth='user', website=True)
    def shorten_url(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        return request.website.render("website_url.page_shorten_url")

    @http.route(['/r/recent_links'], type='json', auth='user')
    def recent_links(self, **post):
        cr, uid, context = request.cr, request.uid, request.context
        return request.registry['website.alias'].recent_links(cr, uid, post['filter'], context=context).to_json()

    @http.route(['/r/archive'], type='json', auth='user', methods=['POST'])
    def archive_link(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        if not 'code' in post:
            return {'error':'No code provided'}

        alias_obj = request.registry['website.alias']
        alias_id = alias_obj.search(cr, uid, [('code', '=', post['code'])])
        alias = alias_obj.browse(cr, uid, alias_id, context=context)

        return alias.archive()

    @http.route(['/r/<string:code>+'] , type='http', auth="user", website=True)
    def statistics_shorten_url(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context

        code_id = request.registry['website.alias.code'].search(cr, uid, [('code', '=', code)])
        code = request.registry['website.alias.code'].browse(cr, uid, code_id, context=context)
        alias = code[0].alias_id

        if alias:
            return request.website.render("website_url.graphs", alias.to_json()[0])
        else:
            return werkzeug.utils.redirect('', 301)

    @http.route(['/r/<string:code>/chart'], type="json", auth="user")
    def chart_data(self, code):
        cr, uid, context = request.cr, request.uid, request.context

        code_obj = request.registry['website.alias.code']
        code_id = code_obj.search(cr, uid, [('code', '=', code)])
        code = code_obj.browse(cr, uid, code_id, context=context)
        alias_id = code[0].alias_id.id

        # Stats on clicks and clicks by countries
        total_clicks = request.registry['website.alias.click'].get_total_clicks(cr, uid, alias_id, context=context)
        clicks_by_day = request.registry['website.alias.click'].get_clicks_by_day(cr, uid, alias_id, context=context)

        clicks_by_country = request.registry['website.alias.click'].get_clicks_by_country(cr, uid, alias_id, context=context)

        last_month_clicks_by_country = request.registry['website.alias.click'].get_last_month_clicks_by_country(cr, uid, alias_id, context=context)
        last_week_clicks_by_country = request.registry['website.alias.click'].get_last_week_clicks_by_country(cr, uid, alias_id, context=context)

        return {'total_clicks':total_clicks, 
                'clicks_by_day':clicks_by_day, 
                'clicks_by_country':clicks_by_country, 
                'last_month_clicks_by_country':last_month_clicks_by_country, 
                'last_week_clicks_by_country':last_week_clicks_by_country}

    @http.route(['/r/<string:code>'] , type='http', auth="none", website=True)
    def full_url_redirect(self, code, **post):
        cr, uid, context = request.cr, request.uid, request.context
        (ip, country_code) = (request.httprequest.remote_addr, request.session['geoip'].get('country_code'))

        redirect_url = request.registry['website.alias'].get_url_from_code(cr, uid, code, ip, country_code, context=context)

        if redirect_url is not None:
            return werkzeug.utils.redirect(redirect_url, 301)
        else:
            return werkzeug.utils.redirect('', 301)

    @http.route(['/r/add_code'], type='json', auth='user')
    def add_code(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        init_code = post['init_code']
        new_code = post['new_code']

        try:
            request.registry['website.alias.code'].add_code(cr, uid, init_code, new_code, context=context)
            return {'new_code':new_code}
        except BaseException:
            return {'error':'The code already exists'}

    # Routes dedicated to the form selects (possibility to create records on the fly
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
        campaign = campaign_obj.create(cr, uid, {'name': post['name']}, context=context)

        return campaign

    @http.route(['/r/mediums/new'], type='json', auth='user', methods=['POST'])
    def new_medium(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        medium_obj = request.registry['crm.tracking.medium']
        medium = medium_obj.create(cr, uid, {'name': post['name']}, context=context)

        return medium

    @http.route(['/r/sources/new'], type='json', auth='user', methods=['POST'])
    def new_source(self, **post):
        cr, uid, context = request.cr, request.uid, request.context

        source_obj = request.registry['crm.tracking.source']
        source = source_obj.create(cr, uid, {'name': post['name']}, context=context)

        return source
