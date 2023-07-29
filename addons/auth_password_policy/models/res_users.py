import logging

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_password_policy(self):
        params = self.env['ir.config_parameter'].sudo()
        return {
            'minlength': int(params.get_param('auth_password_policy.minlength', default=0)),
        }

    def _set_password(self):
        self._check_password_policy(self.mapped('password'))
        super(ResUsers, self)._set_password()

    def _check_password_policy(self, passwords):
        failures = []
        params = self.env['ir.config_parameter'].sudo()

        minlength = int(params.get_param('auth_password_policy.minlength', default=0))
        for password in passwords:
            if not password:
                continue
            if len(password) < minlength:
                failures.append(_(u"Passwords must have at least %d characters, got %d.") % (minlength, len(password)))

        if failures:
            raise UserError(u'\n\n '.join(failures))

    def _password_leak_check_performed(self, is_password_leaked: bool):
        self.ensure_one()
        if is_password_leaked:
            _logger.warning("The password of %s (%s) has been exposed in data breaches.",
                            self.login, request.httprequest.remote_addr)
            self._send_password_leaked_notification()

    def _send_password_leaked_notification(self):
        self.env['bus.bus']._sendone(self.partner_id, 'simple_tagged_notification', {
            'tag': f'password_leaked.{self.partner_id.id}',
            'type': 'danger',
            'message': _(
                "Your password has been exposed in data breaches. "
                "If this system is exposed to untrusted users it is "
                "important to change it immediately for security reasons."),
            'sticky': True,
        })
