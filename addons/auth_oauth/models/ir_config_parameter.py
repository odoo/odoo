# -*- coding: utf-8 -*-

from openerp import models, SUPERUSER_ID


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    def init(self, cr, force=False):
        super(IrConfigParameter, self).init(cr, force=force)
        if force:
            oauth_oe = self.pool['ir.model.data'].xmlid_to_object(
                cr, SUPERUSER_ID, 'auth_oauth.provider_openerp')
            dbuuid = self.get_param(cr, SUPERUSER_ID, 'database.uuid')
            oauth_oe.write({'client_id': dbuuid})
