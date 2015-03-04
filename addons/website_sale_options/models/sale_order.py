# -*- coding: utf-8 -*-
from openerp import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    linked_line_id = fields.Many2one('sale.order.line', 'Linked Order Line', domain="[('order_id','!=',order_id)]", ondelete='cascade')
    option_line_ids = fields.One2many('sale.order.line', 'linked_line_id', string='Options Linked')


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        line_ids = super(SaleOrder, self)._cart_find_product_line(product_id, line_id)
        if line_id:
            return line_ids
        linked_line_id = kwargs.get('linked_line_id')
        optional_product_ids = kwargs.get('optional_product_ids')
        for so in self:
            domain = [('id', 'in', line_ids)]
            domain += linked_line_id and [('linked_line_id', '=', linked_line_id)] or [('linked_line_id', '=', False)]
            if optional_product_ids:
                domain += [('option_line_ids.product_id', '=', pid) for pid in optional_product_ids]
            else:
                domain += [('option_line_ids', '=', False)]
            return self.env['sale.order.line'].sudo().search(domain).ids

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        value = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, kwargs=kwargs)

        linked_line_id = kwargs.get('linked_line_id')
        SaleOrderLine = self.env['sale.order.line'].sudo()
        line = SaleOrderLine.browse(value.get('line_id'))

        for so in self:

            if linked_line_id and linked_line_id in map(int, so.order_line):
                linked = SaleOrderLine.browse(linked_line_id)
                line.write({
                    "name": _("%s\nOption for: %s") % (line.name, linked.product_id.name_get()[0][1]),
                    "linked_line_id": linked_line_id
                })

            # select linked product
            options = so.order_line.filtered(lambda l: l.linked_line_id.id == line.id)

            if options:
                # update line
                options.product_uom_qty = value.get('quantity')

        value['option_ids'] = options.ids
        return value
