# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ipaddress

from odoo import _, SUPERUSER_ID
from odoo.http import request
from odoo.addons.web.controllers.home import Home as WebHome


def _admin_password_warn(uid):
    if request.params['password'] != 'admin':
        return
    if ipaddress.ip_address(request.httprequest.remote_addr).is_private:
        return
    env = request.env(user=SUPERUSER_ID, su=True)
    admin = env.ref('base.partner_admin')
    if uid not in admin.user_ids.ids:
        return
    has_demo = bool(env['ir.module.module'].search_count([('demo', '=', True)]))
    if has_demo:
        return
    admin.with_context(request.env(user=uid)["res.users"].context_get())._bus_send(
        "simple_notification",
        {
            "type": "danger",
            "message": _(
                "Your password is the default (admin)! If this system is exposed to untrusted users it is important to change it immediately for security reasons. I will keep nagging you about it!"
            ),
            "sticky": True,
        },
    )


class Home(WebHome):
    def _login_redirect(self, uid, redirect=None):
        if request.params.get('login_success'):
            _admin_password_warn(uid)
        return super()._login_redirect(uid, redirect)
