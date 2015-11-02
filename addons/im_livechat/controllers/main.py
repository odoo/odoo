# -*- coding: utf-8 -*-
from openerp import http, _
from openerp.http import request
from openerp.addons.base.ir.ir_qweb import AssetsBundle
from openerp.addons.web.controllers.main import binary_content
import base64


class LivechatController(http.Controller):

    @http.route('/im_livechat/external_lib.<any(css,js):ext>', type='http', auth='none')
    def livechat_lib(self, ext, **kwargs):
        asset = AssetsBundle("im_livechat.external_lib")
        mock_attachment = getattr(asset, ext)()
        if isinstance(mock_attachment, list):  # suppose that CSS asset will not required to be split in pages
            mock_attachment = mock_attachment[0]
        # can't use /web/content directly because we don't have attachment ids (attachments must be created)
        status, headers, content = binary_content(id=mock_attachment.id, unique=asset.checksum)
        content_base64 = base64.b64decode(content) if content else ''
        headers.append(('Content-Length', len(content_base64)))
        return request.make_response(content_base64, headers)

    @http.route('/im_livechat/support/<int:channel_id>', type='http', auth='public')
    def support_page(self, channel_id, **kwargs):
        channel = request.env['im_livechat.channel'].sudo().browse(channel_id)
        return request.render('im_livechat.support_page', {'channel': channel})

    @http.route('/im_livechat/loader/<int:channel_id>', type='http', auth='public')
    def loader(self, channel_id, **kwargs):
        username = kwargs.get("username", _("Visitor"))
        channel = request.env['im_livechat.channel'].sudo().browse(channel_id)
        info = request.env['im_livechat.channel'].match_rules(request, channel.id, username=username)
        return request.render('im_livechat.loader', {'info': info, 'web_session_required': True}) if info else False

    @http.route('/im_livechat/get_session', type="json", auth='public')
    def get_session(self, channel_id, anonymous_name, **kwargs):
        # if geoip, add the country name to the anonymous name
        if request.session.geoip:
            anonymous_name = anonymous_name + " ("+request.session.geoip.get('country_name', "")+")"
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.session.uid:
            anonymous_name = request.env.user.name
        return request.env["im_livechat.channel"].get_mail_channel(channel_id, anonymous_name)

    @http.route('/im_livechat/feedback', type='json', auth='public')
    def feedback(self, uuid, rate, reason=None, **kwargs):
        Channel = request.env['mail.channel']
        Rating = request.env['rating.rating']
        channel = Channel.sudo().search([('uuid', '=', uuid)], limit=1)
        if channel:
            # limit the creation : only ONE rating per session
            values = {
                'rating': rate,
            }
            if not channel.rating_ids:
                values.update({
                    'res_id': channel.id,
                    'res_model': 'mail.channel',
                    'rating': rate,
                    'feedback': reason,
                })
                # find the partner (operator)
                if channel.channel_partner_ids:
                    values['rated_partner_id'] = channel.channel_partner_ids[0] and channel.channel_partner_ids[0].id or False
                # create the rating
                rating = Rating.sudo().create(values)
            else:
                if reason:
                    values['feedback'] = reason
                rating = channel.rating_ids[0]
                rating.write(values)
            return rating.id
        return False
