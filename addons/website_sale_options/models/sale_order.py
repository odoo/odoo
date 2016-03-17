# -*- coding: utf-8 -*-

from openerp import SUPERUSER_ID, api
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

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        lines = super(sale_order, self)._cart_find_product_line(product_id, line_id)
        if line_id:
            return lines
        linked_line_id = kwargs.get('linked_line_id', False)
        optional_product_ids = set(kwargs.get('optional_product_ids', []))

        lines = lines.filtered(lambda line: line.linked_line_id.id == linked_line_id)
        if optional_product_ids:
            # only match the lines with the same chosen optional products on the existing lines
            lines = lines.filtered(lambda line: optional_product_ids == set(line.mapped('option_line_ids.product_id.id')))
        else:
            lines = lines.filtered(lambda line: not line.option_line_ids)
        return lines

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
