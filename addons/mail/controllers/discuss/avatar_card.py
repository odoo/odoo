# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context


class AvatarCardController(http.Controller):
    @http.route("/discuss/avatar_card", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def avatar_card(self, user_id, partner_id, fields):
        if not user_id and partner_id:
            partner = request.env["res.partner"].browse(partner_id).exists()
            if not partner:
                return False
            users = partner.user_ids.filtered(lambda u: u.active).with_prefetch(partner.user_ids.ids)
            if not users and partner.id == request.env["ir.model.data"]._xmlid_to_res_id("base.partner_root"):
                user_id = request.env["ir.model.data"]._xmlid_to_res_id("base.user_root")
                return request.env["res.users"].with_context(active_test=False).search_read(
                    [("id", "=", user_id)], fields
                )[0]
            user_id = users.sorted(lambda u: (not u.share, -u.id), reverse=True)[:1]
        if user := request.env["res.users"].search_read([("id", "=", user_id)], fields):
            return user[0]
        return False
