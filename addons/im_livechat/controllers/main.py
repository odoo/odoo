# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup
from werkzeug.exceptions import NotFound
from urllib.parse import urlsplit
from pytz import timezone

from odoo import http, _
from odoo.http import content_disposition, request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.mail.tools.discuss import add_guest_to_context, Store


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

    def _is_cors_request(self):
        headers = request.httprequest.headers
        origin_url = urlsplit(headers.get("referer"))
        return (
            origin_url.netloc != headers.get("host")
            or origin_url.scheme != request.httprequest.scheme
        )

    @http.route('/im_livechat/assets_embed.<any(css, js):ext>', type='http', auth='public', cors='*')
    def assets_embed(self, ext, **kwargs):
        # If the request comes from a different origin, we must provide the CORS
        # assets to enable the redirection of routes to the CORS controller.
        bundle = "im_livechat.assets_embed_cors" if self._is_cors_request() else "im_livechat.assets_embed_external"
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

    def _process_extra_channel_params(self, **kwargs):
        # non_persisted_channel_params, persisted_channel_params
        return {}, {}

    def _get_guest_name(self):
        return _("Visitor")

    @http.route('/im_livechat/get_session', methods=["POST"], type="jsonrpc", auth='public')
    @add_guest_to_context
    def get_session(self, channel_id, previous_operator_id=None, chatbot_script_id=None, persisted=True, **kwargs):
        channel = request.env["discuss.channel"]
        country = request.env["res.country"]
        guest = request.env["mail.guest"]
        store = Store()
        livechat_channel = (
            request.env["im_livechat.channel"]
            .with_context(lang=False)
            .sudo()
            .search([("id", "=", channel_id)])
        )
        if not livechat_channel:
            raise NotFound()
        if not request.env.user._is_public():
            country = request.env.user.country_id
        elif request.geoip.country_code:
            country = request.env["res.country"].search(
                [("code", "=", request.geoip.country_code)], limit=1
            )
        operator_info = livechat_channel._get_operator_info(
            previous_operator_id=previous_operator_id,
            chatbot_script_id=chatbot_script_id,
            country_id=country.id,
            lang=request.cookies.get("frontend_lang"),
            **kwargs
        )
        if not operator_info['operator_partner']:
            return False

        chatbot_script = operator_info['chatbot_script']
        is_chatbot_script = operator_info['operator_model'] == 'chatbot.script'
        non_persisted_channel_params, persisted_channel_params = self._process_extra_channel_params(**kwargs)

        if not persisted:
            channel_id = -1  # only one temporary thread at a time, id does not matter.
            chatbot_data = None
            if is_chatbot_script:
                welcome_steps = chatbot_script._get_welcome_steps()
                chatbot_data = {
                    "script": chatbot_script.id,
                    "steps": welcome_steps.mapped(lambda s: {"scriptStep": s.id}),
                }
                store.add(chatbot_script)
                store.add(welcome_steps)
            channel_info = {
                "fetchChannelInfoState": "fetched",
                "id": channel_id,
                "isLoaded": True,
                "livechat_operator_id": Store.One(
                    operator_info["operator_partner"], self.env["discuss.channel"]._store_livechat_operator_id_fields(),
                ),
                "scrollUnread": False,
                "channel_type": "livechat",
                "chatbot": chatbot_data,
                **non_persisted_channel_params,
            }
            store.add_model_values("discuss.channel", channel_info)
        else:
            if request.env.user._is_public():
                guest = guest.sudo()._get_or_create_guest(
                    guest_name=self._get_guest_name(),
                    country_code=request.geoip.country_code,
                    timezone=request.env["mail.guest"]._get_timezone_from_request(request),
                )
                livechat_channel = livechat_channel.with_context(guest=guest)
                request.update_context(guest=guest)
            channel_vals = livechat_channel._get_livechat_discuss_channel_vals(**operator_info)
            channel_vals.update(**persisted_channel_params)
            lang = request.env["res.lang"].search(
                [("code", "=", request.cookies.get("frontend_lang"))]
            )
            channel_vals.update({"country_id": country.id, "livechat_lang_id": lang.id})
            channel = request.env['discuss.channel'].with_context(
                lang=request.env['chatbot.script']._get_chatbot_language()
            ).sudo().create(channel_vals)
            channel_id = channel.id
            if is_chatbot_script:
                chatbot_script._post_welcome_steps(channel)
            if not is_chatbot_script or chatbot_script.operator_partner_id != channel.livechat_operator_id:
                channel._broadcast([channel.livechat_operator_id.id])
            if guest:
                store.add_global_values(guest_token=guest.sudo()._format_auth_cookie())
        request.env["res.users"]._init_store_data(store)
        # Make sure not to send "isLoaded" value on the guest bus, otherwise it
        # could be overwritten.
        if channel:
             store.add(
                 channel,
                 extra_fields={
                     "isLoaded": not is_chatbot_script,
                     "scrollUnread": False,
                 },
             )
        if not request.env.user._is_public():
            store.add(
                request.env.user.partner_id,
                {"email": request.env.user.partner_id.email},
            )
        return {
            "store_data": store.get_result(),
            "channel_id": channel_id,
        }

    def _post_feedback_message(self, channel, rating, reason):
        body = Markup(
            """<div class="o_mail_notification o_hide_author">"""
            """%(rating)s: <img class="o_livechat_emoji_rating" src="%(rating_url)s" alt="rating"/>%(reason)s"""
            """</div>"""
        ) % {
            "rating": _("Rating"),
            "rating_url": rating.rating_image_url,
            "reason": nl2br("\n" + reason) if reason else "",
        }
        # sudo: discuss.channel - not necessary for posting, but necessary to update related rating
        channel.sudo().message_post(
            body=body,
            message_type="notification",
            rating_id=rating.id,
            subtype_xmlid="mail.mt_comment",
        )

    @http.route("/im_livechat/feedback", type="jsonrpc", auth="public")
    @add_guest_to_context
    def feedback(self, channel_id, rate, reason=None, **kwargs):
        if channel := request.env["discuss.channel"].search([("id", "=", channel_id)]):
            # limit the creation : only ONE rating per session
            values = {
                'rating': rate,
                'consumed': True,
                'feedback': reason,
                'is_internal': False,
            }
            # sudo: rating.rating - visitor can access rating to check if
            # feedback was already given
            if not channel.sudo().rating_ids:
                values.update({
                    'res_id': channel.id,
                    'res_model_id': request.env['ir.model']._get_id('discuss.channel'),
                })
                # sudo: res.partner - visitor must find the operator to rate
                if channel.sudo().channel_partner_ids:
                    values['rated_partner_id'] = channel.channel_partner_ids[0].id
                # if logged in user, set its partner on rating
                values['partner_id'] = request.env.user.partner_id.id if request.session.uid else False
                # create the rating
                rating = request.env['rating.rating'].sudo().create(values)
            else:
                rating = channel.rating_ids[0]
                # sudo: rating.rating - guest or portal user can update their livechat rating
                rating.sudo().write(values)
            self._post_feedback_message(channel, rating, reason)
            return rating.id
        return False

    @http.route("/im_livechat/history", type="jsonrpc", auth="public")
    @add_guest_to_context
    def history_pages(self, pid, channel_id, page_history=None):
        if channel := request.env["discuss.channel"].search([("id", "=", channel_id)]):
            if pid in channel.sudo().channel_member_ids.partner_id.ids:
                request.env["res.partner"].browse(pid)._bus_send_history_message(channel, page_history)

    @http.route("/im_livechat/email_livechat_transcript", type="jsonrpc", auth="user")
    @add_guest_to_context
    def email_livechat_transcript(self, channel_id, email):
        if channel := request.env["discuss.channel"].search([("id", "=", channel_id)]):
            channel._email_livechat_transcript(
                email if not request.env.user.share else request.env.user.email,
            )

    @http.route("/im_livechat/download_transcript/<int:channel_id>", type="http", auth="public")
    @add_guest_to_context
    def download_livechat_transcript(self, channel_id):
        channel = request.env["discuss.channel"].search([("id", "=", channel_id)])
        if not channel:
            raise NotFound()
        partner, guest = request.env["res.partner"]._get_current_persona()
        tz = timezone(partner.tz or guest.timezone or "UTC")
        pdf, _type = (
            request.env["ir.actions.report"]
            .sudo()
            ._render_qweb_pdf(
                "im_livechat.action_report_livechat_conversation",
                channel.ids,
                data={"company": request.env.company, "tz": tz},
            )
        )
        headers = [
            ("Content-Disposition", content_disposition(f"transcript_{channel.id}.pdf", "inline")),
            ("Content-Length", len(pdf)),
            ("Content-Type", "application/pdf"),
        ]
        return request.make_response(pdf, headers=headers)

    @http.route("/im_livechat/visitor_leave_session", type="jsonrpc", auth="public")
    @add_guest_to_context
    def visitor_leave_session(self, channel_id):
        """Called when the livechat visitor leaves the conversation.
        This will clean the chat request and warn the operator that the conversation is over.
        This allows also to re-send a new chat request to the visitor, as while the visitor is
        in conversation with an operator, it's not possible to send the visitor a chat request."""
        if channel := request.env["discuss.channel"].search([("id", "=", channel_id)]):
            channel._close_livechat_session()
