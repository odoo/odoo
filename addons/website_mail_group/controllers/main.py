# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class WebsiteMailGroup(http.Controller):
    @http.route('/groups/is_member', type='json', auth='public', website=True)
    def groups_is_member(self, group_id=0, email=None, **kw):
        """Return the email of the member if found, otherwise None."""
        group = request.env['mail.group'].browse(int(group_id)).exists()
        if not group:
            return

        try:
            group.check_access_rights('read')
            group.check_access_rule('read')
        except AccessError:
            return

        if not request.env.user._is_public():
            email = request.env.user.email
            partner_id = request.env.user.partner_id.id
        else:
            partner_id = None

        member = group.sudo()._find_member(email, partner_id)

        return {
            'is_member': bool(member),
            'email': member.email if member else email,
        }
