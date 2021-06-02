# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import http,tools, _
from odoo.http import request
from odoo.addons.base.models.assetsbundle import AssetsBundle


class LivechatController(http.Controller):

    # Note: the `cors` attribute on many routes is meant to allow the livechat
    # to be embedded in an external website.

    @http.route('/im_livechat/external_lib.<any(css,js):ext>', type='http', auth='public')
    def livechat_lib(self, ext, **kwargs):
        # _get_asset return the bundle html code (script and link list) but we want to use the attachment content
        xmlid = 'im_livechat.external_lib'
        files, remains = request.env["ir.qweb"]._get_asset_content(xmlid, options=request.context)
        asset = AssetsBundle(xmlid, files)

        mock_attachment = getattr(asset, ext)()
        if isinstance(mock_attachment, list):  # suppose that CSS asset will not required to be split in pages
            mock_attachment = mock_attachment[0]
        # can't use /web/content directly because we don't have attachment ids (attachments must be created)
        status, headers, content = request.env['ir.http'].binary_content(id=mock_attachment.id, unique=asset.checksum)
        content_base64 = base64.b64decode(content) if content else ''
        headers.append(('Content-Length', len(content_base64)))
        return request.make_response(content_base64, headers)

    @http.route('/im_livechat/load_templates', type='json', auth='none', cors="*")
    def load_templates(self, **kwargs):
        base_url = request.httprequest.base_url
        templates = [
            'mail/static/src/xml/abstract_thread_window.xml',
            'mail/static/src/xml/discuss.xml',
            'mail/static/src/xml/thread.xml',
            'im_livechat/static/src/xml/im_livechat.xml',
        ]
        return [tools.file_open(tmpl, 'rb').read() for tmpl in templates]

    @http.route('/im_livechat/support/<int:channel_id>', type='http', auth='public')
    def support_page(self, channel_id, **kwargs):
        channel = request.env['im_livechat.channel'].sudo().browse(channel_id)
        return request.render('im_livechat.support_page', {'channel': channel})

    @http.route('/im_livechat/loader/<int:channel_id>', type='http', auth='public')
    def loader(self, channel_id, **kwargs):
        username = kwargs.get("username", _("Visitor"))
        channel = request.env['im_livechat.channel'].sudo().browse(channel_id)
        info = channel.get_livechat_info(username=username)
        return request.render('im_livechat.loader', {'info': info, 'web_session_required': True}, headers=[('Content-Type', 'application/javascript')])

    @http.route('/im_livechat/init', type='json', auth="public", cors="*")
    def livechat_init(self, channel_id):
        available = len(request.env['im_livechat.channel'].sudo().browse(channel_id)._get_available_users())
        rule = {}
        if available:
            # find the country from the request
            country_id = False
            country_code = request.session.geoip and request.session.geoip.get('country_code') or False
            if country_code:
                country_ids = request.env['res.country'].sudo().search([('code', '=', country_code)])
                if country_ids:
                    country_id = country_ids[0].id
            # extract url
            url = request.httprequest.headers.get('Referer')
            # find the first matching rule for the given country and url
            matching_rule = request.env['im_livechat.channel.rule'].sudo().match_rule(channel_id, url, country_id)
            if matching_rule:
                rule = {
                    'action': matching_rule.action,
                    'auto_popup_timer': matching_rule.auto_popup_timer,
                    'regex_url': matching_rule.regex_url,
                }
        return {
            'available_for_me': available and (not rule or rule['action'] != 'hide_button'),
            'rule': rule,
        }

    @http.route('/im_livechat/get_session', type="json", auth='public', cors="*")
    def get_session(self, channel_id, anonymous_name, previous_operator_id=None, **kwargs):
        user_id = None
        country_id = None
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.session.uid:
            user_id = request.env.user.id
            country_id = request.env.user.country_id.id
        else:
            # if geoip, add the country name to the anonymous name
            if request.session.geoip:
                # get the country of the anonymous person, if any
                country_code = request.session.geoip.get('country_code', "")
                country = request.env['res.country'].sudo().search([('code', '=', country_code)], limit=1) if country_code else None
                if country:
                    anonymous_name = "%s (%s)" % (anonymous_name, country.name)
                    country_id = country.id

        if previous_operator_id:
            previous_operator_id = int(previous_operator_id)

        return request.env["im_livechat.channel"].with_context(lang=False).sudo().browse(channel_id)._open_livechat_mail_channel(anonymous_name, previous_operator_id, user_id, country_id)

    @http.route('/im_livechat/feedback', type='json', auth='public', cors="*")
    def feedback(self, uuid, rate, reason=None, **kwargs):
        Channel = request.env['mail.channel']
        channel = Channel.sudo().search([('uuid', '=', uuid)], limit=1)
        if channel:
            # limit the creation : only ONE rating per session
            values = {
                'rating': rate,
                'consumed': True,
                'feedback': reason,
            }
            if not channel.rating_ids:
                res_model_id = request.env['ir.model'].sudo().search([('model', '=', channel._name)], limit=1).id
                values.update({
                    'res_id': channel.id,
                    'res_model_id': res_model_id,
                })
                # find the partner (operator)
                if channel.channel_partner_ids:
                    values['rated_partner_id'] = channel.channel_partner_ids[0] and channel.channel_partner_ids[0].id or False
                # if logged in user, set its partner on rating
                values['partner_id'] = request.env.user.partner_id.id if request.session.uid else False
                # create the rating
                rating = request.env['rating.rating'].sudo().create(values)
            else:
                rating = channel.rating_ids[0]
                rating.write(values)
            return rating.id
        return False

    @http.route('/im_livechat/history', type="json", auth="public", cors="*")
    def history_pages(self, pid, channel_uuid, page_history=None):
        partner_ids = (pid, request.env.user.partner_id.id)
        channel = request.env['mail.channel'].sudo().search([('uuid', '=', channel_uuid), ('channel_partner_ids', 'in', partner_ids)])
        if channel:
            channel._send_history_message(pid, page_history)
        return True

    @http.route('/im_livechat/notify_typing', type='json', auth='public', cors="*")
    def notify_typing(self, uuid, is_typing):
        """ Broadcast the typing notification of the website user to other channel members
            :param uuid: (string) the UUID of the livechat channel
            :param is_typing: (boolean) tells whether the website user is typing or not.
        """
        Channel = request.env['mail.channel']
        channel = Channel.sudo().search([('uuid', '=', uuid)], limit=1)
        channel.notify_typing(is_typing=is_typing, is_website_user=True)

    @http.route('/im_livechat/email_livechat_transcript', type='json', auth='public', cors="*")
    def email_livechat_transcript(self, uuid, email):
        channel = request.env['mail.channel'].sudo().search([('uuid', '=', uuid)], limit=1)
        if channel:
            channel._email_livechat_transcript(email)
