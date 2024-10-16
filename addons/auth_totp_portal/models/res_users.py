# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import auth_totp


class ResUsers(auth_totp.ResUsers):

    def get_totp_invite_url(self):
        if not self._is_internal():
            return '/my/security'
        else:
            return super().get_totp_invite_url()
