# -*- coding: utf-8 -*-
from openerp import SUPERUSER_ID
from openerp.osv import osv

class ir_configparameter(osv.Model):
    _inherit = 'ir.config_parameter'

    def init(self, cr, force=False):
        super(ir_configparameter, self).init(cr, force=force)
        if force:
            IMD = self.pool['ir.model.data']
            oauth_oe = IMD.xmlid_to_object(cr, SUPERUSER_ID, 'auth_oauth.provider_openerp')
            if not oauth_oe:
                return
            dbuuid = self.get_param(cr, SUPERUSER_ID, 'database.uuid')
            oauth_oe.write({'client_id': dbuuid})
