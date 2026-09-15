from odoo import http
from odoo.http import request
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class WebsiteMailGroup(http.Controller):
    @http.route("/group/is_member", type="jsonrpc", auth="public", website=True)
    def group_is_member(self, group_id=0, email=None, **kw):
        group = request.env["mail.group"].browse(int(group_id)).exists()
        if not group:
            return None

        token = kw.get("token")

        if token and token != group._generate_group_access_token():
            _debug.logic("group_membership_bad_token", group=group)
            return None

        if token:
            group = group.sudo()

        if not group.has_access("read"):
            _debug.logic(
                "group_membership_no_read_access", group=group, tokened=bool(token)
            )
            return None

        if not request.env.user._is_public():
            email = request.env.user.email_normalized
            partner_id = request.env.user.partner_id.id
        else:
            partner_id = None

        member = group.sudo()._find_member(email, partner_id)
        _debug.logic(
            "group_membership_resolved",
            group=group,
            member=member,
            by_partner=bool(partner_id),
        )

        return {
            "is_member": bool(member),
            "email": member.email if member else email,
        }
