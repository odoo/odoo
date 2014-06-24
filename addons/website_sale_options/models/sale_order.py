# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID
from openerp.osv import osv, orm, fields
from openerp.addons.web.http import request
from openerp.tools.translate import _


class sale_order(osv.Model):
    _inherit = "sale.order"

    def _cart_find_product_line(self, cr, uid, ids, product_id=None, line_id=None, linked_line_id=None, optional_product_ids=None, context=None):
        for so in self.browse(cr, uid, ids, context=context):

            domain = [('order_id', '=', so.id), ('product_id', '=', product_id)]
            if line_id:
                domain += [('id', '=', line_id)]
            domain += linked_line_id and [('linked_line_id', '=', linked_line_id)] or [('linked_line_id', '=', False)]
            if not line_id:
                if optional_product_ids:
                    domain += [('option_line_ids.product_id', '=', pid) for pid in optional_product_ids]
                else:
                    domain += [('option_line_ids', '=', False)]

            order_line_id = None
            order_line_ids = self.pool.get('sale.order.line').search(cr, SUPERUSER_ID, domain, context=context)
            if order_line_ids:
                order_line_id = order_line_ids[0]
            return order_line_id

    def _cart_update(self, cr, uid, ids, product_id=None, line_id=None, add_qty=0, set_qty=0, linked_line_id=None, optional_product_ids=None, context=None):
        """ Add or set product quantity, add_qty can be negative """
        sol = self.pool.get('sale.order.line')

        quantity = 0
        for so in self.browse(cr, uid, ids, context=context):
            line_id = so._cart_find_product_line(product_id, line_id, linked_line_id, optional_product_ids, context=context)

            # Create line if no line with product_id can be located
            if not line_id:
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, context=context)
                if linked_line_id and linked_line_id in map(int,so.order_line):
                    values["linked_line_id"] = linked_line_id
                    linked = sol.browse(cr, SUPERUSER_ID, linked_line_id, context=context)
                    values["name"] = _("%s\nLinked to: %s") % (values["name"], linked.product_id.name_get()[0][1])
                line_id = sol.create(cr, SUPERUSER_ID, values, context=context)
                if add_qty:
                    add_qty -= 1

            # compute new quantity
            if set_qty:
                quantity = set_qty
            elif add_qty != None:
                quantity = sol.browse(cr, SUPERUSER_ID, line_id, context=context).product_uom_qty + (add_qty or 0)

            # select linked product
            option_ids = [line.id for line in so.order_line if line.linked_line_id.id == line_id]

            # Remove zero of negative lines
            if quantity <= 0:
                sol.unlink(cr, SUPERUSER_ID, [line_id] + option_ids, context=context)
            else:
                # update line
                values = self._website_product_id_change(cr, uid, ids, so.id, product_id, line_id, context=context)
                values['product_uom_qty'] = quantity
                sol.write(cr, SUPERUSER_ID, [line_id], values, context=context)

                # change quantity of linked product
                if option_ids:
                    sol.write(cr, SUPERUSER_ID, option_ids, {'product_uom_qty': quantity}, context=context)

        return (line_id, quantity)
