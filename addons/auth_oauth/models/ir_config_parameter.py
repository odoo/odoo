# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import mail


class IrConfig_Parameter(mail.IrConfig_Parameter):

    def init(self, force=False):
        super().init(force=force)
        if force:
            oauth_oe = self.env.ref('auth_oauth.provider_openerp')
            if not oauth_oe:
                return
            dbuuid = self.sudo().get_param('database.uuid')
            oauth_oe.write({'client_id': dbuuid})
