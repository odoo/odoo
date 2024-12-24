from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.osv import expression
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.portal.utils import get_portal_partner


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

    @http.route("/portal/chatter_init", type="jsonrpc", auth="public", website=True)
    def portal_chatter_init(self, thread_model, thread_id, **kwargs):
        store = Store()
        thread = request.env[thread_model]._get_thread_with_access(thread_id, **kwargs)
        partner = request.env.user.partner_id
        if thread and request.env.user._is_public():
            if portal_partner := get_portal_partner(
                thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
            ):
                partner = portal_partner
        store.add_global_values(
            store_self=Store.One(partner, ["active", "name", "user", "write_date"])
        )
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(partner, {"is_user_publisher": True})
        return store.get_result()

    @http.route('/mail/chatter_fetch', type='jsonrpc', auth='public', website=True)
    def portal_message_fetch(self, thread_model, thread_id, fetch_params=None, **kw):
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
        res = Message._message_fetch(domain, **(fetch_params or {}))
        messages = res.pop("messages")
        return {
            **res,
            "data": {"mail.message": messages.portal_message_format(options=kw)},
            "messages": messages.ids,
        }

    def _setup_portal_message_fetch_extra_domain(self, data):
        return []

    @http.route(['/mail/update_is_internal'], type='jsonrpc', auth="user", website=True)
    def portal_message_update_is_internal(self, message_id, is_internal):
        message = request.env['mail.message'].browse(int(message_id))
        message.write({'is_internal': is_internal})
        return message.is_internal
