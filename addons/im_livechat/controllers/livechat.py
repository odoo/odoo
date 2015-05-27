# -*- coding: utf-8 -*-
import json
import openerp
import openerp.addons.im_chat.im_chat

from openerp import http
from openerp.http import request


class LivechatController(http.Controller):

    @http.route('/im_livechat/support/<im_livechat.channel:channel_id>', type='http', auth='none')
    def support_page(self, channel_id, **kwargs):
        info["channel"] = channel_id
        return request.render('im_livechat.support_page', info)

    @http.route('/im_livechat/loader/<im_livechat.channel:channel_id>', type='http', auth='none')
    def loader(self, dbname, channel_id, **kwargs):
        username = kwargs.get("username", "Visitor")
        info = request.env['im_livechat.channel'].match_rules(request, channel_id, username=username)
        return request.render('im_livechat.loader', {'info': info}) if info else False

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
    def available(self, channel):
        request.env['im_livechat.channel'].get_available_users(channel) > 0

