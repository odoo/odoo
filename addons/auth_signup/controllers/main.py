# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import werkzeug
from werkzeug.urls import url_encode

from odoo import http, tools, _
from odoo.addons.auth_signup.models.res_users import SignupError
from odoo.addons.auth_signup.models.res_partner import now
from odoo.addons.web.controllers.home import ensure_db, Home, SIGN_UP_REQUEST_PARAMS, LOGIN_SUCCESSFUL_PARAMS
from odoo.addons.base_setup.controllers.main import BaseSetup
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)

LOGIN_SUCCESSFUL_PARAMS.add('account_created')


class AuthSignupHome(Home):

    @http.route()
    def web_login(self, *args, **kw):
        ensure_db()
        response = super().web_login(*args, **kw)
        response.qcontext.update(self.get_auth_signup_config())
        if request.session.uid:
            if request.httprequest.method == 'GET' and request.params.get('redirect'):
                # Redirect if already logged in and redirect param is present
                return request.redirect(request.params.get('redirect'))
            # Add message for non-internal user account without redirect if account was just created
            if response.location == '/web/login_successful' and kw.get('confirm_password'):
                return request.redirect_query('/web/login_successful', query={'account_created': True})
        return response

    @http.route('/web/signup', type='http', auth='public', website=True, sitemap=False)
    def web_auth_signup(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                # Send an account creation confirmation email
                if qcontext.get('token') or qcontext.get('b2c_email_activate_enabled'):
                    User = request.env['res.users']

                    # new user created with b2c_email_activate_enabled, still inactive
                    if not qcontext.get('token'):
                        User = User.with_context(active_test=False)

                    user_sudo = User.sudo().search(
                        User._get_login_domain(qcontext.get('login')), order=User._get_login_order(), limit=1
                    )
                    template = request.env.ref('auth_signup.mail_template_user_signup_account_created', raise_if_not_found=False)
                    if user_sudo and template:

                        # new user created with b2c_email_activate_enabled, inactive, need an activation token
                        if not qcontext.get('token'):
                            return self._send_activation_email(user_sudo, qcontext)

                        template.sudo().send_mail(user_sudo.id, force_send=True)
                return self.web_login(*args, **kw)
            except UserError as e:
                qcontext['error'] = e.args[0]
            except (SignupError, AssertionError) as e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _("Another user is already registered using this email address.")
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _("Could not create a new account.")

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search([('email', '=', qcontext.get('signup_email')), ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'}))

        response = request.render('auth_signup.signup', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/web/reset_password', type='http', auth='public', website=True, sitemap=False)
    def web_auth_reset_password(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('reset_password_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                if qcontext.get('token'):
                    self.do_signup(qcontext)
                    return self.web_login(*args, **kw)
                else:
                    login = qcontext.get('login')
                    assert login, _("No login provided.")
                    _logger.info(
                        "Password reset attempt for <%s> by user <%s> from %s",
                        login, request.env.user.login, request.httprequest.remote_addr)
                    request.env['res.users'].sudo().reset_password(login)
                    qcontext['message'] = _("Password reset instructions sent to your email")
            except UserError as e:
                qcontext['error'] = e.args[0]
            except SignupError:
                qcontext['error'] = _("Could not reset your password")
                _logger.exception('error when resetting password')
            except Exception as e:
                qcontext['error'] = str(e)

        elif 'signup_email' in qcontext:
            user = request.env['res.users'].sudo().search([('email', '=', qcontext.get('signup_email')), ('state', '!=', 'new')], limit=1)
            if user:
                return request.redirect('/web/login?%s' % url_encode({'login': user.login, 'redirect': '/web'}))

        response = request.render('auth_signup.reset_password', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

    @http.route('/web/activate', type='http', auth='public', website=True, sitemap=False)
    def web_auth_activate(self, *args, **kw):
        qcontext = self.get_auth_signup_qcontext(include_inactive=True)
        partner = request.env['res.partner'].sudo().with_context(active_test=False)\
            .search([('signup_token', '=', qcontext.get('token')), ('email', '=', qcontext.get('login'))], limit=1)
        partner_user = partner.user_ids[0]
        if not qcontext.get('token') or 'error' in qcontext or not partner or not partner_user:
            raise werkzeug.exceptions.NotFound()

        partner_user.sudo().write({'active': True})
        partner.write({'signup_token': False})

        # notify about new account creation, if it set
        notification_receiver_email = request.env['ir.config_parameter'].sudo()\
            .get_param('auth_signup.account_activated_notification_receiver')
        notification_receiver_partner = request.env['res.partner'].sudo().\
            search([('email', '=', notification_receiver_email)], limit=1)
        if notification_receiver_partner:
            template = request.env.ref('auth_signup.account_activated_notification_email')
            template.sudo().send_mail(partner_user.id, force_send=True,
                                      email_values={'recipient_ids': [notification_receiver_partner[0].id]})

        return request.redirect('/web/login')

    def get_auth_signup_config(self):
        """retrieve the module config (which features are enabled) for the login page"""

        get_param = request.env['ir.config_parameter'].sudo().get_param
        signup_invitation_scope = request.env['res.users']._get_signup_invitation_scope()
        return {
            'disable_database_manager': not tools.config['list_db'],
            'signup_enabled': signup_invitation_scope in ('b2c', 'b2c_email_activate'),
            'b2c_email_activate_enabled': signup_invitation_scope == 'b2c_email_activate',
            'reset_password_enabled': get_param('auth_signup.reset_password') == 'True',
        }

    def get_auth_signup_qcontext(self, include_inactive=False):
        """ Shared helper returning the rendering context for signup and reset password """
        qcontext = {k: v for (k, v) in request.params.items() if k in SIGN_UP_REQUEST_PARAMS}
        qcontext.update(self.get_auth_signup_config())
        if not qcontext.get('token') and request.session.get('auth_signup_token'):
            qcontext['token'] = request.session.get('auth_signup_token')
        if qcontext.get('token'):
            try:
                # retrieve the user info (name, login or email) corresponding to a signup token
                token_infos = request.env['res.partner'].sudo().signup_retrieve_info(qcontext.get('token'), include_inactive)
                for k, v in token_infos.items():
                    qcontext.setdefault(k, v)
            except:
                qcontext['error'] = _("Invalid signup token")
                qcontext['invalid_token'] = True
        return qcontext

    def _prepare_signup_values(self, qcontext):
        values = { key: qcontext.get(key) for key in ('login', 'name', 'password') }
        if not values:
            raise UserError(_("The form was not properly filled in."))
        if values.get('password') != qcontext.get('confirm_password'):
            raise UserError(_("Passwords do not match; please retype them."))
        supported_lang_codes = [code for code, _ in request.env['res.lang'].get_installed()]
        lang = request.context.get('lang', '')
        if lang in supported_lang_codes:
            values['lang'] = lang
        return values

    def do_signup(self, qcontext):
        """ Shared helper that creates a res.partner out of a token """
        values = self._prepare_signup_values(qcontext)
        self._signup_with_values(qcontext.get('token'), values, qcontext.get('b2c_email_activate_enabled'))
        request.env.cr.commit()

    def _signup_with_values(self, token, values, b2c_email_activate_enabled):
        login, password = request.env['res.users'].sudo().signup(values, token)
        request.env.cr.commit()     # as authenticate will use its own cursor we need to commit the current transaction
        if b2c_email_activate_enabled and not token:
            return
        pre_uid = request.session.authenticate(request.db, login, password)
        if not pre_uid:
            raise SignupError(_('Authentication Failed.'))

    def _send_activation_email(self, user_sudo, qcontext):
        user_sudo.mapped('partner_id').signup_prepare(signup_type="activate", expiration=now(weeks=+1))
        template = request.env.ref('auth_signup.account_activate_email')
        template.sudo().send_mail(user_sudo.id, force_send=True)

        qcontext['message'] = _("Account activation instructions sent to your email")
        response = request.render('auth_signup.activate_account', qcontext)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response

class AuthBaseSetup(BaseSetup):
    @http.route('/base_setup/data', type='json', auth='user')
    def base_setup_data(self, **kwargs):
        res = super().base_setup_data(**kwargs)
        res.update({'resend_invitation': True})
        return res
