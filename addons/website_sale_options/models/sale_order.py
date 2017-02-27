# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    linked_line_id = fields.Many2one('sale.order.line', string='Linked Order Line', domain="[('order_id', '!=', order_id)]", ondelete='cascade')
    option_line_ids = fields.One2many('sale.order.line', 'linked_line_id', string='Options Linked')


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _cart_find_product_line(self, product_id=None, line_id=None, **kwargs):
        self.ensure_one()
        lines = super(SaleOrder, self)._cart_find_product_line(product_id, line_id)
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

    @api.multi
    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        self.ensure_one()
        """ Add or set product quantity, add_qty can be negative """
        value = super(SaleOrder, self)._cart_update(product_id, line_id, add_qty, set_qty, **kwargs)
        SaleOrderLineSudo = self.env['sale.order.line'].sudo()
        line = SaleOrderLineSudo.browse(value.get('line_id'))
        # link a product to the sales order
        if kwargs.get('linked_line_id'):
            linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
            line.write({
                'linked_line_id': linked_line.id,
                'name': line.name + "\n" + _("Option for:") + ' ' + linked_line.product_id.display_name,
            })
            linked_line.write({"name": linked_line.name + "\n" + _("Option:") + ' ' + line.product_id.display_name})

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == line.id)
        for option_line_id in option_lines:
            super(SaleOrder, self)._cart_update(option_line_id.product_id.id, option_line_id.id, add_qty, set_qty, **kwargs)

        value['option_ids'] = list(set(option_lines.ids))
        return value
