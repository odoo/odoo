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
        registry = openerp.modules.registry.RegistryManager.get(dbname)
        username = kwargs.get("username", "Visitor")
        info = registry.get('im_livechat.channel').match_rules(request.cr, request.uid, request, dbname, channel_id, username=username, context=request.context)
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
    def available(self, db, channel):
        cr, uid, context, db = request.cr, request.session.uid or openerp.SUPERUSER_ID, request.context, request.db
        reg = openerp.modules.registry.RegistryManager.get(db)
        with reg.cursor() as cr:
            return len(reg.get('im_livechat.channel').get_available_users(cr, uid, channel)) > 0

