# -*- coding: utf-8 -*-
from odoo import models


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def init(self, force=False):
        super(IrConfigParameter, self).init(force=force)
        if force:
            oauth_oe = self.env.ref('auth_oauth.provider_openerp')
            oauth_oe.write({'client_id': self.sudo().get_param('database.uuid')})
