# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _sale_order_count(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        partner_ids = self.browse(cr, uid, ids, context)

        def _recursive_count(partner):
            if partner.id not in res:
                res[partner.id] = 0
                try:
                    res[partner.id] = len(partner.sale_order_ids)
                    for child_partner in partner.child_ids:
                        res[partner.id] += _recursive_count(child_partner)
                except:
                    pass
            return res[partner.id]

        for partner in partner_ids:
            _recursive_count(partner)
        return res

    _columns = {
        'sale_order_count': fields.function(_sale_order_count, string='# of Sales Order', type='integer'),
        'sale_order_ids': fields.one2many('sale.order','partner_id','Sales Order')
    }
