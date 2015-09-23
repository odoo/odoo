# -*- coding: utf-8 -*-

from openerp.osv import osv, fields


class sale_order_line(osv.Model):
    _inherit = "sale.order.line"
    _columns = {
        'linked_line_id': fields.many2one('sale.order.line', 'Linked Order Line', domain="[('order_id','!=',order_id)]", ondelete='cascade'),
        'option_line_ids': fields.one2many('sale.order.line', 'linked_line_id', string='Options Linked'),
    }
