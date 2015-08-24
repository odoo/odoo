# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _claim_count(self, cr, uid, ids, field_name, arg, context=None):
        Claim = self.pool['crm.claim']
        return {
            partner_id: Claim.search_count(cr,uid, [('partner_id', '=', partner_id)], context=context)  
            for partner_id in ids
        }

    _columns = {
        'claim_count': fields.function(_claim_count, string='# Claims', type='integer'),
    }
