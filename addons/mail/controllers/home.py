# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ipaddress

from odoo import _, SUPERUSER_ID
from odoo.http import request
from odoo.addons.web.controllers.home import Home as WebHome

def _admin_password_warn(uid):
    """ Admin still has `admin` password, flash a message via chatter.

    Uses a private mail.channel from the system (/ odoobot) to the user, as
    using a more generic mail.thread could send an email which is undesirable

    Uses mail.channel directly because using mail.thread might send an email instead.
    """
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

    user = request.env(user=uid)['res.users']
    MailChannel = env(context=user.context_get())['mail.channel']
    MailChannel.browse(MailChannel.channel_get([admin.id])['id'])\
        .message_post(
            body=_("Your password is the default (admin)! If this system is exposed to untrusted users it is important to change it immediately for security reasons. I will keep nagging you about it!"),
            message_type='comment',
            subtype_xmlid='mail.mt_comment'
        )

class Home(WebHome):
    def _login_redirect(self, uid, redirect=None):
        if request.params.get('login_success'):
            _admin_password_warn(uid)

        return super()._login_redirect(uid, redirect)
