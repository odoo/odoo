# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.auth_signup.controllers.main import AuthSignupHome
from odoo.addons.web.controllers.home import ensure_db


class HrInviteHome(AuthSignupHome):

    @http.route('/hr/invite/<string:access_token>', type='http', auth='public')
    def hr_invite(self, access_token, **kw):
        """Public entry point of an HR invitation link: validate the token then
        hand over to the (revamped) standard signup form."""
        ensure_db()
        link = request.env['hr.invitation.link'].sudo().with_context(active_test=False).search(
            [('access_token', '=', access_token)], limit=1)
        if not link:
            raise werkzeug.exceptions.NotFound()
        ok, reason = link._is_valid()
        if not ok:
            return request.render('hr.invite_invalid', {'reason': reason})
        # Remember the link for the signup POST (which carries no token in its URL).
        request.session['hr_invite_link_id'] = link.id
        return request.redirect('/web/signup')

    def get_auth_signup_qcontext(self):
        qcontext = super().get_auth_signup_qcontext()
        if request.session.get('hr_invite_link_id'):
            # An invitation link is its own authorization: allow the signup form
            # even when global signup is disabled (b2b), and flag it for the view.
            qcontext['signup_enabled'] = True
            qcontext['hr_invite'] = True
        return qcontext

    def do_signup(self, qcontext, do_login=True):
        link_id = request.session.get('hr_invite_link_id')
        if link_id:
            # Route res.users.signup() to lite-user provisioning + link enforcement.
            request.update_context(hr_invite_link_id=link_id)
        res = super().do_signup(qcontext, do_login)
        if link_id:
            # Only reached when the signup succeeded (do_signup raises otherwise).
            request.session.pop('hr_invite_link_id', None)
        return res
