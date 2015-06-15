# -*- coding: utf-8 -*-
import json
import openerp
import openerp.addons.im_chat.im_chat
from openerp.addons.base.ir.ir_qweb import AssetsBundle, QWebTemplateNotFound

from openerp import http
from openerp import SUPERUSER_ID
from openerp.http import request


class LivechatController(http.Controller):

    @http.route('/im_livechat/support/<int:channel_id>', type='http', auth='none')
    def support_page(self, channel_id, **kwargs):
        info = kwargs or {}
        info["channel"] = request.env['im_livechat.channel'].sudo().browse(channel_id)
        info['url'] = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return request.render('im_livechat.support_page', info)

    @http.route('/im_livechat/loader/<int:channel_id>', type='http', auth='none')
    def loader(self, channel_id, **kwargs):
        """ Return the js bundle 'im_livechat.external_lib' concatened with the 'im_livechat.loader' template.
            This aims to fetch all the javascript code required by the livechat at once.
            It returns False, if no rules match with the URL, or if the URL is blocked by a rule
        """
        username = kwargs.get("username", "Visitor")
        info = request.env['im_livechat.channel'].match_rules(request, channel_id, username=username)
        if info:
            try:
                bundle = AssetsBundle('im_livechat.external_lib', uid=SUPERUSER_ID)
                bundle_js = bundle.js()
                bundle_js += request.env.ref('im_livechat.loader').render({'info': info})
                return bundle_js
            except QWebTemplateNotFound:
                return False
        return False

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
        return request.env['im_livechat.channel'].get_available_users(channel) > 0
