# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _


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
        value = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)

        SaleOrderLineSudo = self.env['sale.order.line'].sudo()
        line = SaleOrderLineSudo.browse(value.get('line_id'))

        # link a product to the sale order
        if kwargs.get('linked_line_id'):
            linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
            line.write({
                    "name": _("%s\nOption for: %s") % (line.name, linked_line.product_id.name_get()[0][1]),
                    "linked_line_id": linked_line.id
                })

        value['option_ids'] = set()
        for so in self:
            # select all optional products linked to the updated line
            option_lines = so.order_line.filtered(lambda l: l.linked_line_id.id == line.id)

            # update line
            for option_line_id in option_lines:
                super(SaleOrder, self)._cart_update(option_line_id.product_id.id, option_line_id.id, add_qty, set_qty, **kwargs)
                option_line_id.write({"name": _("%s\nOption for: %s") % (option_line_id.name, option_line_id.linked_line_id.product_id.name_get()[0][1])})
                value['option_ids'].add(option_line_id.id)

        value['option_ids'] = list(value['option_ids'])

        return value
