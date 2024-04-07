# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
import re
from werkzeug.exceptions import NotFound
from urllib.parse import urlsplit

from odoo import http, tools, _, release
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import replace_exceptions
from odoo.addons.base.models.assetsbundle import AssetsBundle
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context


class LivechatController(http.Controller):

    # Note: the `cors` attribute on many routes is meant to allow the livechat
    # to be embedded in an external website.

    @http.route('/im_livechat/external_lib.<any(css,js):ext>', type='http', auth='public', cors='*')
    def external_lib(self, ext, **kwargs):
        """ Preserve compatibility with legacy livechat imports. Only
        serves javascript since the css will be fetched by the shadow
        DOM of the livechat to avoid conflicts.
        """
        if ext == 'css':
            raise request.not_found()
        return self.assets_embed(ext, **kwargs)

    @http.route('/im_livechat/assets_embed.<any(css, js):ext>', type='http', auth='public', cors='*')
    def assets_embed(self, ext, **kwargs):
        # If the request comes from a different origin, we must provide the CORS
        # assets to enable the redirection of routes to the CORS controller.
        headers = request.httprequest.headers
        origin_url = urlsplit(headers.get('referer'))
        bundle = 'im_livechat.assets_embed_external'
        if origin_url.netloc != headers.get('host') or origin_url.scheme != request.httprequest.scheme:
            bundle = 'im_livechat.assets_embed_cors'
        asset = request.env["ir.qweb"]._get_asset_bundle(bundle)
        if ext not in ('css', 'js'):
            raise request.not_found()
        stream = request.env['ir.binary']._get_stream_from(getattr(asset, ext)())
        return stream.get_response()

    @http.route('/im_livechat/font-awesome', type='http', auth='none', cors="*")
    def fontawesome(self, **kwargs):
        return http.Stream.from_path('web/static/src/libs/fontawesome/fonts/fontawesome-webfont.woff2').get_response()

    @http.route('/im_livechat/odoo_ui_icons', type='http', auth='none', cors="*")
    def odoo_ui_icons(self, **kwargs):
        return http.Stream.from_path('web/static/lib/odoo_ui_icons/fonts/odoo_ui_icons.woff2').get_response()

    @http.route('/im_livechat/emoji_bundle', type='http', auth='public', cors='*')
    def get_emoji_bundle(self):
        bundle = 'web.assets_emoji'
        asset = request.env["ir.qweb"]._get_asset_bundle(bundle)
        stream = request.env['ir.binary']._get_stream_from(asset.js())
        return stream.get_response()

    @http.route('/im_livechat/support/<int:channel_id>', type='http', auth='public')
    def support_page(self, channel_id, **kwargs):
        channel = request.env['im_livechat.channel'].sudo().browse(channel_id)
        return request.render('im_livechat.support_page', {'channel': channel})

    @http.route('/im_livechat/loader/<int:channel_id>', type='http', auth='public')
    def loader(self, channel_id, **kwargs):
        username = kwargs.get("username", _("Visitor"))
        channel = request.env['im_livechat.channel'].sudo().browse(channel_id)
        info = channel.get_livechat_info(username=username)
        return request.render('im_livechat.loader', {'info': info}, headers=[('Content-Type', 'application/javascript')])

    @http.route('/im_livechat/init', type='json', auth="public", cors="*")
    def livechat_init(self, channel_id):
        operator_available = len(request.env['im_livechat.channel'].sudo().browse(channel_id).available_operator_ids)
        rule = {}
        # find the country from the request
        country_id = False
        if request.geoip.country_code:
            country_id = request.env['res.country'].sudo().search([('code', '=', request.geoip.country_code)], limit=1).id
        # extract url
        url = request.httprequest.headers.get('Referer')
        # find the first matching rule for the given country and url
        matching_rule = request.env['im_livechat.channel.rule'].sudo().match_rule(channel_id, url, country_id)
        if matching_rule and (not matching_rule.chatbot_script_id or matching_rule.chatbot_script_id.script_step_ids):
            frontend_lang = request.httprequest.cookies.get('frontend_lang', request.env.user.lang or 'en_US')
            matching_rule = matching_rule.with_context(lang=frontend_lang)
            rule = {
                'action': matching_rule.action,
                'auto_popup_timer': matching_rule.auto_popup_timer,
                'regex_url': matching_rule.regex_url,
            }
            if matching_rule.chatbot_script_id.active and (not matching_rule.chatbot_only_if_no_operator or
               (not operator_available and matching_rule.chatbot_only_if_no_operator)) and matching_rule.chatbot_script_id.script_step_ids:
                chatbot_script = matching_rule.chatbot_script_id
                rule.update({'chatbot': chatbot_script._format_for_frontend()})
        return {
            'odoo_version': release.version,
            'available_for_me': (rule and rule.get('chatbot'))
                                or operator_available and (not rule or rule['action'] != 'hide_button'),
            'rule': rule,
        }

    @http.route('/im_livechat/operator/<int:operator_id>/avatar',
        type='http', auth="public", cors="*")
    def livechat_operator_get_avatar(self, operator_id):
        """ Custom route allowing to retrieve an operator's avatar.

        This is done to bypass more complicated rules, notably 'website_published' when the website
        module is installed.

        Here, we assume that if you are a member of at least one im_livechat.channel, then it's ok
        to make your avatar publicly available.

        We also make the chatbot operator avatars publicly available. """

        is_livechat_member = False
        operator = request.env['res.partner'].sudo().browse(operator_id)
        if operator.exists():
            is_livechat_member = bool(request.env['im_livechat.channel'].sudo().search_count([
                ('user_ids', 'in', operator.user_ids.ids)
            ]))

        if not is_livechat_member:
            # we don't put chatbot operators as livechat members (because we don't have a user_id for them)
            is_livechat_member = bool(request.env['chatbot.script'].sudo().search_count([
                ('operator_partner_id', 'in', operator.ids)
            ]))

        return request.env['ir.binary']._get_image_stream_from(
            operator if is_livechat_member else request.env['res.partner'],
            field_name='avatar_128',
            placeholder='mail/static/src/img/smiley/avatar.jpg',
        ).get_response()

    def _get_guest_name(self):
        return _("Visitor")

    @http.route('/im_livechat/get_session', methods=["POST"], type="json", auth='public')
    @add_guest_to_context
    def get_session(self, channel_id, anonymous_name, previous_operator_id=None, chatbot_script_id=None, persisted=True, **kwargs):
        user_id = None
        country_id = None
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.session.uid:
            user_id = request.env.user.id
            country_id = request.env.user.country_id.id
        else:
            # if geoip, add the country name to the anonymous name
            if request.geoip.country_code:
                # get the country of the anonymous person, if any
                country = request.env['res.country'].sudo().search([('code', '=', request.geoip.country_code)], limit=1)
                if country:
                    country_id = country.id

        if previous_operator_id:
            previous_operator_id = int(previous_operator_id)

        chatbot_script = False
        if chatbot_script_id:
            frontend_lang = request.httprequest.cookies.get('frontend_lang', request.env.user.lang or 'en_US')
            chatbot_script = request.env['chatbot.script'].sudo().with_context(lang=frontend_lang).browse(chatbot_script_id)
        channel_vals = request.env["im_livechat.channel"].with_context(lang=False).sudo().browse(channel_id)._get_livechat_discuss_channel_vals(
            anonymous_name,
            previous_operator_id=previous_operator_id,
            chatbot_script=chatbot_script,
            user_id=user_id,
            country_id=country_id,
            lang=request.httprequest.cookies.get('frontend_lang')
        )
        if not channel_vals:
            return False
        if not persisted:
            operator_partner = request.env['res.partner'].sudo().browse(channel_vals['livechat_operator_id'])
            display_name = operator_partner.user_livechat_username or operator_partner.display_name
            return {
                'name': channel_vals['name'],
                'chatbot_current_step_id': channel_vals['chatbot_current_step_id'],
                'state': 'open',
                'operator_pid': (operator_partner.id, display_name.replace(',', '')),
                'chatbot_script_id': chatbot_script.id if chatbot_script else None
            }
        channel = request.env['discuss.channel'].with_context(mail_create_nosubscribe=False).sudo().create(channel_vals)
        with replace_exceptions(UserError, by=NotFound()):
            # sudo: mail.guest - creating a guest and their member in a dedicated channel created from livechat
            __, guest = channel.sudo()._find_or_create_persona_for_channel(
                guest_name=self._get_guest_name(),
                country_code=request.geoip.country_code,
                timezone=request.env['mail.guest']._get_timezone_from_request(request),
                post_joined_message=False
            )
        channel = channel.with_context(guest=guest)  # a new guest was possibly created
        if not chatbot_script or chatbot_script.operator_partner_id != channel.livechat_operator_id:
            channel._broadcast([channel.livechat_operator_id.id])
        channel_info = channel._channel_info()[0]
        if guest:
            channel_info['guest_token'] = guest._format_auth_cookie()
        return channel_info

    def _post_feedback_message(self, channel, rating, reason):
        reason = Markup("<br>" + re.sub(r'\r\n|\r|\n', "<br>", reason) if reason else "")
        body = Markup('''
            <div class="o_mail_notification o_hide_author">
                %(rating)s: <img class="o_livechat_emoji_rating" src="%(rating_url)s" alt="rating"/>%(reason)s
            </div>
        ''') % {
            'rating': _('Rating'),
            'rating_url': rating.rating_image_url,
            'reason': reason,
        }
        channel.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_comment')

    @http.route('/im_livechat/feedback', type='json', auth='public', cors="*")
    def feedback(self, uuid, rate, reason=None, **kwargs):
        channel = request.env['discuss.channel'].sudo().search([('uuid', '=', uuid)], limit=1)
        if channel:
            # limit the creation : only ONE rating per session
            values = {
                'rating': rate,
                'consumed': True,
                'feedback': reason,
                'is_internal': False,
            }
            if not channel.rating_ids:
                values.update({
                    'res_id': channel.id,
                    'res_model_id': request.env['ir.model']._get_id('discuss.channel'),
                })
                # find the partner (operator)
                if channel.channel_partner_ids:
                    values['rated_partner_id'] = channel.channel_partner_ids[0].id
                # if logged in user, set its partner on rating
                values['partner_id'] = request.env.user.partner_id.id if request.session.uid else False
                # create the rating
                rating = request.env['rating.rating'].sudo().create(values)
            else:
                rating = channel.rating_ids[0]
                rating.write(values)
            self._post_feedback_message(channel, rating, reason)
            return rating.id
        return False

    @http.route('/im_livechat/history', type="json", auth="public", cors="*")
    def history_pages(self, pid, channel_uuid, page_history=None):
        partner_ids = (pid, request.env.user.partner_id.id)
        channel = request.env['discuss.channel'].sudo().search([('uuid', '=', channel_uuid), ('channel_partner_ids', 'in', partner_ids)])
        if channel:
            channel._send_history_message(pid, page_history)
        return True

    @http.route('/im_livechat/email_livechat_transcript', type='json', auth='public', cors="*")
    def email_livechat_transcript(self, uuid, email):
        channel = request.env['discuss.channel'].sudo().search([
            ('channel_type', '=', 'livechat'),
            ('uuid', '=', uuid)], limit=1)
        if channel:
            channel._email_livechat_transcript(email)

    @http.route("/im_livechat/visitor_leave_session", type="json", auth="public")
    @add_guest_to_context
    def visitor_leave_session(self, uuid):
        """Called when the livechat visitor leaves the conversation.
        This will clean the chat request and warn the operator that the conversation is over.
        This allows also to re-send a new chat request to the visitor, as while the visitor is
        in conversation with an operator, it's not possible to send the visitor a chat request."""
        # sudo: channel access is validated with uuid
        channel_sudo = request.env["discuss.channel"].sudo().search([("uuid", "=", uuid)])
        if not channel_sudo:
            return
        domain = [("channel_id", "=", channel_sudo.id), ("is_self", "=", True)]
        member = request.env["discuss.channel.member"].search(domain)
        # sudo: discuss.channel.rtc.session - member of current user can leave call
        member.sudo()._rtc_leave_call()
        channel_sudo._close_livechat_session()
