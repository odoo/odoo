# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.mail.tools.discuss import add_guest_to_context


class AvatarCardController(http.Controller):
    @http.route("/discuss/avatar_card", methods=["POST"], type="jsonrpc", auth="public")
    @add_guest_to_context
    def avatar_card(self, user_id, partner_id, fields):
        if not user_id and partner_id:
            if partner_id == request.env["ir.model.data"]._xmlid_to_res_id("base.partner_root"):
                return request.env.ref("base.user_root").read(fields)[0]
            partner = request.env["res.partner"].search([("id", "=", partner_id)])
            if not partner:
                return False
            user_id = partner.user_ids.sorted(lambda u: (not u.share, -u.id), reverse=True)[:1].id
        if user := request.env["res.users"].search_read([("id", "=", user_id)], fields):
            return user[0]
        return False
