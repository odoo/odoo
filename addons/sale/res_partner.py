# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields,osv

class res_partner(osv.osv):
    _inherit = 'res.partner'

    def _sale_order_count(self, cr, uid, ids, field_name, arg, context=None):
        res = dict(map(lambda x: (x,0), ids))
        # The current user may not have access rights for sale orders
        try:
            for partner in self.browse(cr, uid, ids, context):
                res[partner.id] = len(partner.sale_order_ids) + len(partner.mapped('child_ids.sale_order_ids'))
        except:
            pass
        return res

    _columns = {
        'sale_order_count': fields.function(_sale_order_count, string='# of Sales Order', type='integer'),
        'sale_order_ids': fields.one2many('sale.order','partner_id','Sales Order')
    }
