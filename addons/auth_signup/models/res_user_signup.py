# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import uuid

from ast import literal_eval
from passlib.context import CryptContext
from werkzeug.urls import url_encode

from odoo import fields, models, tools, _
from odoo.addons.base.models.ir_mail_server import MailDeliveryException
from odoo.tools import sql

_logger = logging.getLogger(__name__)


class ResUsersSignup(models.TransientModel):
    """ User class. A res.users.signup record models a user waiting
        to be confirmed via mail.

        res.users.signup class is totally separated from res.users.
        It aims to create a non persistent user entry which doesn't
        block an email address if the account is not validated.
    """
    _name = "res.users.signup"
    _description = "User waiting for confirmation"
    _transient_max_hours = 24

    login = fields.Char()
    email = fields.Char()
    name = fields.Char()
    password = fields.Char(
        compute='_compute_password', inverse='_set_password',
        invisible=False, copy=False,
        help="Keep empty if you don't want the user to be able to connect on the system."
        )
    lang = fields.Char()

    token = fields.Char()

    mails_counter = fields.Integer(default=0)

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, help='The default company for this user.')

    _sql_constraints = [
        ('login_key', 'UNIQUE (login)', 'You can not have two users with the same login!')
    ]

    def init(self):
        super().init()
        if not sql.column_exists(self.env.cr, self._table, "password"):
            self.env.cr.execute("ALTER TABLE res_users_signup ADD COLUMN password varchar")

    def signup(self, values):
        self.email = self.login
        self.token = uuid.uuid4().hex
        self.send_mail()
        return self.id

    def _compute_password(self):
        for user in self:
            user.password = ''

    def _set_password(self):
        ctx = self.env.user._crypt_context()
        for user in self:
            self._set_encrypted_password(user.id, ctx.hash(user.password))

    def _set_encrypted_password(self, uid, pw):
        assert self.env.user._crypt_context().identify(pw) != 'plaintext'

        self.env.cr.execute(
            'UPDATE res_users_signup SET password=%s WHERE id=%s',
            (pw, uid)
        )
        self.browse(uid).invalidate_recordset(['password'])

    def send_mail(self):
        if self._allowed_mail():
            url = "%s/web/confirm?%s" % (self.get_base_url(), url_encode({'token': self.token}))
            try:
                template = self.env.ref('auth_signup.confirm_signup_email')
                assert template._name == 'mail.template'
                email_values = {
                        'email_cc': False,
                        'auto_delete': False,
                        'message_type': 'user_notification',
                        'recipient_ids': [],
                        'partner_ids': [],
                        'scheduled_date': False,
                    }
                context = {'url': url}
                email_values['email_to'] = self.login
                template.sudo().with_context(context).send_mail(self.id, raise_exception=True, email_values=email_values)
                self.mails_counter += 1
                _logger.info("Registration confirmation mail sent to <%s>", self.email)
            except MailDeliveryException as e:
                _logger.warning("Error mail delivery error encountered while sending confirmation email, message: %s", e)
            return True
        else:
            return False

    def _allowed_mail(self):
        if self.mails_counter < 3:
            return True
        elif self.write_date < fields.Datetime.add(fields.Datetime.now(), seconds=-30):
            return True
        else:
            return False

    def confirm_account(self):
        values = {
            'login':self.login,
            'name':self.name,
            'password':self.password,
            'lang':self.lang,
            'email':self.email
        }

        template_user_id = literal_eval(self.env['ir.config_parameter'].sudo().get_param('base.template_portal_user_id', 'False'))
        template_user = self.env['res.users'].browse(template_user_id)
        if not template_user.exists():
            raise ValueError(_('Signup: invalid template user'))

        values['active'] = True
        user = template_user.with_context(no_reset_password=True).copy(values)

        self.env.cr.execute(
            'SELECT password FROM res_users_signup WHERE login=%s',
            (self.login,)
        )
        password = self.env.cr.fetchone()
        self.env.cr.execute(
                'UPDATE res_users SET password=%s WHERE login=%s',
                (password, self.login)
            )
        self.unlink()
        return user
