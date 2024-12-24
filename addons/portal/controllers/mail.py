# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug import urls
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.tools import consteq
from odoo.addons.mail.controllers import mail
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.portal.utils import get_portal_partner
from odoo.exceptions import AccessError


class PortalChatter(http.Controller):

    def _portal_post_check_attachments(self, attachment_ids, attachment_tokens):
        request.env['ir.attachment'].browse(attachment_ids)._check_attachments_access(attachment_tokens)

    def _portal_post_has_content(self, thread_model, thread_id, message, attachment_ids=None, **kw):
        """ Tells if we can effectively post on the model based on content. """
        return bool(message) or bool(attachment_ids)

    @http.route('/mail/avatar/mail.message/<int:res_id>/author_avatar/<int:width>x<int:height>', type='http', auth='public')
    def portal_avatar(self, res_id=None, height=50, width=50, access_token=None, _hash=None, pid=None):
        """Get the avatar image in the chatter of the portal"""
        if access_token or (_hash and pid):
            message = request.env["mail.message"].browse(int(res_id)).exists().filtered(
                lambda msg: request.env[msg.model]._get_thread_with_access(
                    msg.res_id, token=access_token, hash=_hash, pid=pid and int(pid)
                )
            )
        else:
            message = request.env.ref('web.image_placeholder').sudo()
        # in case there is no message, it creates a stream with the placeholder image
        stream = request.env['ir.binary']._get_image_stream_from(
            message, field_name='author_avatar', width=int(width), height=int(height),
        )
        return stream.get_response()

    @http.route("/portal/chatter_init", type="json", auth="public", website=True)
    def portal_chatter_init(self, thread_model, thread_id, **kwargs):
        store = Store()
        thread = request.env[thread_model]._get_thread_with_access(thread_id, **kwargs)
        partner = request.env.user.partner_id
        if thread and request.env.user._is_public():
            if portal_partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                partner = portal_partner
        store.add({"self": Store.one(partner, fields=["active", "name", "user", "write_date"])})
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(partner, {"is_user_publisher": True})
        return store.get_result()

    @http.route('/mail/chatter_fetch', type='json', auth='public', website=True)
    def portal_message_fetch(
            self, thread_model, thread_id, limit=10, after=None, before=None, **kw
    ):
        # Only search into website_message_ids, so apply the same domain to perform only one search
        # extract domain from the 'website_message_ids' field
        model = request.env[thread_model]
        field = model._fields['website_message_ids']
        domain = expression.AND([
            self._setup_portal_message_fetch_extra_domain(kw),
            field.get_domain_list(model),
            [('res_id', '=', thread_id), '|', ('body', '!=', ''), ('attachment_ids', '!=', False),
             ("subtype_id", "=", request.env.ref("mail.mt_comment").id)]
        ])

        # Check access
        Message = request.env['mail.message']
        if kw.get('token'):
            access_as_sudo = request.env[thread_model]._get_thread_with_access(
                thread_id, token=kw.get("token")
            )
            if not access_as_sudo:  # if token is not correct, raise Forbidden
                raise Forbidden()
            # Non-employee see only messages with not internal subtype (aka, no internal logs)
            if not request.env.user._is_internal():
                domain = expression.AND([Message._get_search_domain_share(), domain])
            Message = request.env["mail.message"].sudo()
        res = Message._message_fetch(domain, None, before, after, None, limit)
        messages = res.pop("messages")
        return {
            **res,
            "data": {"mail.message": messages.portal_message_format(options=kw)},
            "messages": Store.many_ids(messages),
        }

    def _setup_portal_message_fetch_extra_domain(self, data):
        return []

    @http.route(['/mail/update_is_internal'], type='json', auth="user", website=True)
    def portal_message_update_is_internal(self, message_id, is_internal):
        message = request.env['mail.message'].browse(int(message_id))
        message.write({'is_internal': is_internal})
        return message.is_internal


class MailController(mail.MailController):

    @classmethod
    def _redirect_to_record(cls, model, res_id, access_token=None, **kwargs):
        """ If the current user doesn't have access to the document, but provided
        a valid access token, redirect them to the front-end view.
        If the partner_id and hash parameters are given, add those parameters to the redirect url
        to authentify the recipient in the chatter, if any.

        :param model: the model name of the record that will be visualized
        :param res_id: the id of the record
        :param access_token: token that gives access to the record
            bypassing the rights and rules restriction of the user.
        :param kwargs: Typically, it can receive a partner_id and a hash (sign_token).
            If so, those two parameters are used to authentify the recipient in the chatter, if any.
        :return:
        """
        # no model / res_id, meaning no possible record -> direct skip to super
        if not model or not res_id or model not in request.env:
            return super(MailController, cls)._redirect_to_record(model, res_id, access_token=access_token, **kwargs)

        if isinstance(request.env[model], request.env.registry['portal.mixin']):
            uid = request.session.uid or request.env.ref('base.public_user').id
            record_sudo = request.env[model].sudo().browse(res_id).exists()
            try:
                record_sudo.with_user(uid).check_access('read')
            except AccessError:
                if record_sudo.access_token and access_token and consteq(record_sudo.access_token, access_token):
                    record_action = record_sudo._get_access_action(force_website=True)
                    if record_action['type'] == 'ir.actions.act_url':
                        pid = kwargs.get('pid')
                        hash = kwargs.get('hash')
                        url = record_action['url']
                        if pid and hash:
                            url = urls.url_parse(url)
                            url_params = url.decode_query()
                            url_params.update([("pid", pid), ("hash", hash)])
                            url = url.replace(query=urls.url_encode(url_params)).to_url()
                        return request.redirect(url)
        return super(MailController, cls)._redirect_to_record(model, res_id, access_token=access_token, **kwargs)

    # Add website=True to support the portal layout
    @http.route('/mail/unfollow', type='http', website=True)
    def mail_action_unfollow(self, model, res_id, pid, token, **kwargs):
        return super().mail_action_unfollow(model, res_id, pid, token, **kwargs)
