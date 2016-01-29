# -*- coding: utf-8 -*-
import json
import openerp
import openerp.addons.im_chat.im_chat

from openerp import http
from openerp.http import request


class LivechatController(http.Controller):

    @http.route('/im_livechat/support/<string:dbname>/<int:channel_id>', type='http', auth='none')
    def support_page(self, dbname, channel_id, **kwargs):
        registry, cr, uid, context = openerp.modules.registry.RegistryManager.get(dbname), request.cr, openerp.SUPERUSER_ID, request.context
        info = registry.get('im_livechat.channel').get_info_for_chat_src(cr, uid, channel_id)
        info["dbname"] = dbname
        info["channel"] = channel_id
        info["channel_name"] = registry.get('im_livechat.channel').read(cr, uid, channel_id, ['name'], context=context)["name"]
        return request.render('im_livechat.support_page', info)

    @http.route('/im_livechat/loader/<string:dbname>/<int:channel_id>', type='http', auth='none')
    def loader(self, dbname, channel_id, **kwargs):
        registry, cr, uid, context = openerp.modules.registry.RegistryManager.get(dbname), request.cr, openerp.SUPERUSER_ID, request.context
        info = registry.get('im_livechat.channel').get_info_for_chat_src(cr, uid, channel_id)
        info["dbname"] = dbname
        info["channel"] = channel_id
        info["username"] = kwargs.get("username", "Visitor")
        # find the country from the request
        country_id = False
        country_code = request.session.geoip and request.session.geoip.get('country_code') or False
        if country_code:
            country_ids = registry.get('res.country').search(cr, uid, [('code', '=', country_code)], context=context)
            if country_ids:
                country_id = country_ids[0]
        # extract url
        url = request.httprequest.headers.get('Referer') or request.httprequest.base_url
        # find the match rule for the given country and url
        rule = registry.get('im_livechat.channel.rule').match_rule(cr, uid, channel_id, url, country_id, context=context)
        if rule:
            if rule.action == 'hide_button':
                # don't return the initialization script, since its blocked (in the country)
                return
            rule_data = {
                'action' : rule.action,
                'auto_popup_timer' : rule.auto_popup_timer,
                'regex_url' : rule.regex_url,
            }
        info['rule'] = json.dumps(rule and rule_data or False)
        return request.render('im_livechat.loader', info, headers=[('Content-Type', 'application/javascript')])

    @http.route('/im_livechat/get_session', type="json", auth="none")
    def get_session(self, channel_id, anonymous_name, **kwargs):
        cr, uid, context, db = request.cr, request.session.uid, request.context, request.db
        reg = openerp.modules.registry.RegistryManager.get(db)
        # if geoip, add the country name to the anonymous name
        if request.session.geoip:
            anonymous_name = anonymous_name + " ("+request.session.geoip.get('country_name', "")+")"
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.session.uid:
            anonymous_name = False
        return reg.get("im_livechat.channel").get_channel_session(cr, uid, channel_id, anonymous_name, context=context)

    @http.route('/im_livechat/available', type='json', auth="none")
    def available(self, db, channel):
        cr, uid, context, db = request.cr, request.session.uid or openerp.SUPERUSER_ID, request.context, request.db
        reg = openerp.modules.registry.RegistryManager.get(db)
        with reg.cursor() as cr:
            return len(reg.get('im_livechat.channel').get_available_users(cr, uid, channel)) > 0

