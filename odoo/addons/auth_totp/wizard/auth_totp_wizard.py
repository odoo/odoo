# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import functools
import io
import qrcode
import re
import werkzeug.urls

from odoo import _, api, fields, models
from odoo.addons.base.models.res_users import check_identity
from odoo.exceptions import UserError
from odoo.http import request

from odoo.addons.auth_totp.models.totp import ALGORITHM, DIGITS, TIMESTEP

compress = functools.partial(re.sub, r'\s', '')

class TOTPWizard(models.TransientModel):
    _name = 'auth_totp.wizard'
    _description = "2-Factor Setup Wizard"

    user_id = fields.Many2one('res.users', required=True, readonly=True)
    secret = fields.Char(required=True, readonly=True)
    url = fields.Char(store=True, readonly=True, compute='_compute_qrcode')
    qrcode = fields.Binary(
        attachment=False, store=True, readonly=True,
        compute='_compute_qrcode',
    )
    code = fields.Char(string="Verification Code", size=7)

    @api.depends('user_id.login', 'user_id.company_id.display_name', 'secret')
    def _compute_qrcode(self):
        # TODO: make "issuer" configurable through config parameter?
        global_issuer = request and request.httprequest.host.split(':', 1)[0]
        for w in self:
            issuer = global_issuer or w.user_id.company_id.display_name
            w.url = url = werkzeug.urls.url_unparse((
                'otpauth', 'totp',
                werkzeug.urls.url_quote(f'{issuer}:{w.user_id.login}', safe=':'),
                werkzeug.urls.url_encode({
                    'secret': compress(w.secret),
                    'issuer': issuer,
                    # apparently a lowercase hash name is anathema to google
                    # authenticator (error) and passlib (no token)
                    'algorithm': ALGORITHM.upper(),
                    'digits': DIGITS,
                    'period': TIMESTEP,
                }), ''
            ))

            data = io.BytesIO()
            qrcode.make(url.encode(), box_size=4).save(data, optimise=True, format='PNG')
            w.qrcode = base64.b64encode(data.getvalue()).decode()

    @check_identity
    def enable(self):
        try:
            c = int(compress(self.code))
        except ValueError:
            raise UserError(_("The verification code should only contain numbers"))
        if self.user_id._totp_try_setting(self.secret, c):
            self.secret = '' # empty it, because why keep it until GC?
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _("2-Factor authentication is now enabled."),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }
        raise UserError(_('Verification failed, please double-check the 6-digit code'))

    def create(self, vals_list):
        rule = self.env.ref('auth_totp.rule_auth_totp_wizard', raise_if_not_found=False)
        if rule and rule.sudo().groups:
            rule.sudo().groups = False
        return super().create(vals_list)
