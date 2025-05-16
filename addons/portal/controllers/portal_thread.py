# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tools.discuss import Store
from odoo.addons.portal.utils import get_portal_partner


class PortalChatter(http.Controller):

    @http.route("/portal/chatter_init", type="jsonrpc", auth="public", website=True)
    def portal_chatter_init(self, thread_model, thread_id, **kwargs):
        store = Store()
        thread = ThreadController._get_thread_with_access(thread_model, thread_id, **kwargs)
        partner = request.env.user.partner_id
        if thread:
            mode = request.env[thread_model]._get_mail_message_access([thread_id], "create")
            has_react_access = ThreadController._get_thread_with_access(thread_model, thread_id, mode, **kwargs)
            can_react = has_react_access
            if request.env.user._is_public():
                portal_partner = get_portal_partner(
                    thread, kwargs.get("hash"), kwargs.get("pid"), kwargs.get("token")
                )
                can_react = has_react_access and portal_partner
                partner = portal_partner or partner
            store.add(thread, {"can_react": bool(can_react)}, as_thread=True)
        store.add_global_values(
            store_self=Store.One(partner, ["active", "avatar_128", "name", "user"])
        )
        if request.env.user.has_group("website.group_website_restricted_editor"):
            store.add(partner, {"is_user_publisher": True})
        return store.get_result()
