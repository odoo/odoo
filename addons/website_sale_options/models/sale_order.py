# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.tools.translate import _


class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, context=None, *args):
        line_ids = super(sale_order, self)._cart_find_product_line(cr, uid, ids, product_id, line_id, context=context)
        linked_line_id = args.get('linked_line_id')
        optional_product_ids = args.get('optional_product_ids')

        for so in self.browse(cr, uid, ids, context=context):
            domain = [('order_id', '=', so.id), ('product_id', '=', product_id), ('id', 'in', line_ids)]
            if line_id:
                domain += [('id', '=', line_id)]
            domain += linked_line_id and [('linked_line_id', '=', linked_line_id)] or [('linked_line_id', '=', False)]
            if not line_id:
                if optional_product_ids:
                    domain += [('option_line_ids.product_id', '=', pid) for pid in optional_product_ids]
                else:
                    domain += [('option_line_ids', '=', False)]

            return self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, context=None, *args):
        """ Add or set product quantity, add_qty can be negative """
        line_id, quantity = super(sale_order, self)._cart_update(cr, uid, ids, product_id, line_id, add_qty, set_qty, context=context, *args)
        linked_line_id = args.get('linked_line_id')
        sol = self.pool.get('sale.order.line')

        for so in self.browse(cr, uid, ids, context=context):
            values = {}

            if linked_line_id and linked_line_id in map(int,so.order_line):
                linked = sol.browse(cr, SUPERUSER_ID, linked_line_id, context=context)
                sol.write(cr, SUPERUSER_ID, [line_id], {
                        "name": _("%s\nOption for: %s") % (values["name"], linked.product_id.name_get()[0][1]),
                        "linked_line_id": linked_line_id
                    }, context=context)

            # select linked product
            option_ids = [line.id for line in so.order_line if line.linked_line_id.id == line_id]

            if option_ids:
                # Remove zero of negative lines
                if quantity <= 0:
                    sol.unlink(cr, SUPERUSER_ID, option_ids, context=context)
                else:
                    # update line
                    sol.write(cr, SUPERUSER_ID, option_ids, {
                            'product_uom_qty': quantity
                        }, context=context)

        return (line_id, quantity)
