# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import SUPERUSER_ID
from openerp.osv import osv


class crm_claim(osv.osv):
    _inherit = "crm.claim"

    def _get_default_partner_id(self, cr, uid, context=None):
        """ Gives default partner_id """
        if context is None:
            context = {}
        if context.get('portal'):
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            # Special case for portal users, as they are not allowed to call name_get on res.partner
            # We save this call for the web client by returning it in default get
            return self.pool['res.partner'].name_get(cr, SUPERUSER_ID, [user.partner_id.id], context=context)[0]
        return False

    _defaults = {
        'partner_id': lambda s, cr, uid, c: s._get_default_partner_id(cr, uid, c),
    }
