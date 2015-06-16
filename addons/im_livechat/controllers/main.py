# -*- coding: utf-8 -*-
import json

from openerp import http, _
from openerp import SUPERUSER_ID
from openerp.http import request


class LivechatController(http.Controller):

    @http.route('/im_livechat/support/<string:dbname>/<int:channel_id>', type='http', auth='none')
    def support_page(self, dbname, channel_id, **kwargs):
        Channel = request.env['im_livechat.channel']
        info = Channel.get_channel_infos(channel_id)
        info["dbname"] = dbname
        info["channel"] = channel_id
        info["channel_name"] = Channel.browse(channel_id).name
        return request.render('im_livechat.support_page', info)

    @http.route('/im_livechat/loader/<string:dbname>/<int:channel_id>', type='http', auth='none')
    def loader(self, dbname, channel_id, **kwargs):
        info = request.env['im_livechat.channel'].sudo().get_channel_infos(channel_id)
        info["dbname"] = dbname
        info["channel"] = channel_id
        info["username"] = kwargs.get("username", _("Visitor"))
        # find the country from the request
        country_id = False
        country_code = request.session.geoip and request.session.geoip.get('country_code') or False
        if country_code:
            countries = request.env['res.country'].search([('code', '=', country_code)])
            if countries:
                country_id = countries[0]
        # extract url
        url = request.httprequest.headers.get('Referer') or request.httprequest.base_url
        # find the match rule for the given country and url
        rule = request.env['im_livechat.channel.rule'].match_rule(channel_id, url, country_id)
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
        return request.render('im_livechat.loader', info)

    @http.route('/im_livechat/get_session', type="json", auth="none")
    def get_session(self, channel_id, anonymous_name, **kwargs):
        # if geoip, add the country name to the anonymous name
        if request.session.geoip:
            anonymous_name = anonymous_name + " ("+request.session.geoip.get('country_name', "")+")"
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.session.uid:
            anonymous_name = False
        return request.env['im_livechat.channel'].sudo(request.session.uid).get_channel_session(channel_id, anonymous_name)

    @http.route('/im_livechat/available', type='json', auth="none")
    def available(self, db, channel):
        user_id = request.session.uid or SUPERUSER_ID
        channel = request.env['im_livechat.channel'].sudo(user_id).browse(channel)
        return len(channel.get_available_users()) > 0

    @http.route('/rating/livechat/feedback', type='json', auth='none')
    def rating_livechat_feedback(self, uuid, rate, reason=None, **kwargs):
        Session = request.env['im_chat.session']
        Rating = request.env['rating.rating']
        session_ids = Session.sudo().search([('uuid', '=', uuid)])
        if session_ids:
            session = session_ids[0]
            # limit the creation : only ONE rating per session
            values = {
                'rating': rate,
            }
            if not session.rating_ids:
                values.update({
                    'res_id': session.id,
                    'res_model': 'im_chat.session',
                    'rating': rate,
                    'feedback': reason,
                })
                # find the partner related to the user of the conversation
                rated_partner_id = False
                if session.user_ids:
                    rated_partner_id = session.user_ids[0] and session.user_ids[0].partner_id.id or False
                    values['rated_partner_id'] = rated_partner_id
                # create the rating
                rating = Rating.sudo().create(values)
            else:
                if reason:
                    values['feedback'] = reason
                rating = session.rating_ids[0]
                rating.write(values)
            return rating.id
        return False
