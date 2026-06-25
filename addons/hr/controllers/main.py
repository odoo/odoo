# Part of Odoo. See LICENSE file for full copyright and licensing details.
import werkzeug

from odoo import _, http
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.http.session import authenticate
from odoo.tools import consteq
from odoo.addons.web.controllers.home import ensure_db, Home


class HrInviteHome(Home):

    @http.route('/hr/invite/<int:link_id>/<string:access_token>', type='http', auth='public', methods=['GET', 'POST'], sitemap=False)
    def hr_invite(self, link_id, access_token, **kw):
        ensure_db()
        link = request.env['hr.invitation.link'].sudo().browse(link_id).exists()
        if not link or not access_token or not link.access_token or not consteq(link.access_token, access_token):
            raise werkzeug.exceptions.NotFound()
        ok, reason = link._is_valid()
        if not ok:
            return request.render('hr.invite_invalid', {'reason': reason})

        qcontext = {
            'link_id': link.id,
            'access_token': access_token,
            'company_name': link.company_id.name,
            'name': kw.get('name', ''),
            'login': kw.get('login', ''),
        }
        if request.httprequest.method == 'POST':
            try:
                uid = self._do_invite_signup(link, kw)
                return request.redirect(self._login_redirect(uid))
            except (UserError, ValidationError) as e:
                qcontext['error'] = e.args[0] if e.args else str(e)
        return request.render('hr.invite_signup', qcontext)

    def _do_invite_signup(self, link, params):
        """Validate the submitted form, provision the Light user/employee and log
        the new user in. Returns the freshly created user id."""
        name = (params.get('name') or '').strip()
        login = (params.get('login') or '').strip()
        password = params.get('password')
        if not (name and login and password):
            raise UserError(_("Please fill in all the required fields."))
        if password != params.get('confirm_password'):
            raise UserError(_("Passwords do not match; please retype them."))
        values = {'name': name, 'login': login, 'password': password}
        login, password = request.env['res.users'].sudo()._signup_from_invitation(values, link.id)
        request.env.cr.commit()
        credential = {'login': login, 'password': password, 'type': 'password'}
        return authenticate(request.session, request.env, credential)['uid']
