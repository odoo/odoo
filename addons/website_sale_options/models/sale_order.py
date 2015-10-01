# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.tools.translate import _


class sale_order_line(osv.Model):
    _inherit = "sale.order.line"
    _columns = {
        'linked_line_id': fields.many2one('sale.order.line', 'Linked Order Line', domain="[('order_id','!=',order_id)]", ondelete='cascade'),
        'option_line_ids': fields.one2many('sale.order.line', 'linked_line_id', string='Options Linked'),
    }

class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None, **kwargs):
        line_ids = super(sale_order, self)._cart_find_product_line(cr, uid, ids, product_id, line_id, context=context)
        if line_id:
            return line_ids
        linked_line_id = kwargs.get('linked_line_id')
        optional_product_ids = kwargs.get('optional_product_ids')
        for so in self.browse(cr, uid, ids, context=context):
            domain = [('id', 'in', line_ids)]
            domain += linked_line_id and [('linked_line_id', '=', linked_line_id)] or [('linked_line_id', '=', False)]
            if optional_product_ids:
                domain += [('option_line_ids.product_id', '=', pid) for pid in optional_product_ids]
            else:
                domain += [('option_line_ids', '=', False)]
            return self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        value = super(sale_order, self)._cart_update(cr, uid, ids, product_id, line_id, add_qty, set_qty, context=context, **kwargs)

        sol = self.pool.get('sale.order.line')
        line = sol.browse(cr, SUPERUSER_ID, value.get('line_id'), context=context)

        # link a product to the sale order
        if kwargs.get('linked_line_id'):
            linked_line_id = sol.browse(cr, SUPERUSER_ID, kwargs['linked_line_id'], context=context)
            line.write({
                    "name": _("%s\nOption for: %s") % (line.name, linked_line_id.product_id.name_get()[0][1]),
                    "linked_line_id": linked_line_id.id
                })

        value['option_ids'] = set()
        for so in self.browse(cr, uid, ids, context=context):
            # select all optional products linked to the updated line
            option_line_ids = [l for l in so.order_line if l.linked_line_id.id == line.id]

            # update line
            for option_line_id in option_line_ids:
                super(sale_order, self)._cart_update(cr, uid, ids, option_line_id.product_id.id, option_line_id.id, add_qty, set_qty, context=context, **kwargs)
                option_line_id.write({"name": _("%s\nOption for: %s") % (option_line_id.name, option_line_id.linked_line_id.product_id.name_get()[0][1])})
                value['option_ids'].add(option_line_id.id)

        value['option_ids'] = list(value['option_ids'])

        return value
