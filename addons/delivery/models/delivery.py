# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models, _
from openerp.exceptions import UserError
from openerp.tools.safe_eval import safe_eval as eval

import openerp.addons.decimal_precision as dp


class DeliveryGrid(models.Model):
    _name = "delivery.grid"
    _description = "Delivery Grid"

    name = fields.Char(string='Grid Name', required=True)
    sequence = fields.Integer(required=True, help="Gives the sequence order when displaying a list of delivery grid.", default=10)
    carrier_id = fields.Many2one('delivery.carrier', string='Carrier', required=True, ondelete='cascade')
    country_ids = fields.Many2many('res.country', string='Countries')
    state_ids = fields.Many2many('res.country.state', string='States')
    zip_from = fields.Char(string='Start Zip', size=12)
    zip_to = fields.Char(string='To Zip', size=12)
    line_ids = fields.One2many('delivery.grid.line', 'grid_id', string='Grid Line', copy=True)
    active = fields.Boolean(help="If the active field is set to False, it will allow you to hide the delivery grid without removing it.", default=True)

    _order = 'sequence'

    @api.multi
    def get_price(self, order, dt):
        quantity = total = volume = weight = 0
        total_delivery = 0.0
        ProductUom = self.env['product.uom']
        SaleOreder = self.env['sale.order']
        for line in order.order_line.filtered(lambda lines: lines.state == 'cancel'):
            if line.is_delivery:
                total_delivery += line.price_subtotal + SaleOreder._amount_line_tax(line)
            if not line.product_id or line.is_delivery:
                continue
            quantities = ProductUom._compute_qty(line.product_uom.id, line.product_uom_qty, line.product_id.uom_id.id)
            weight += (line.product_id.weight or 0.0) * quantities
            volume += (line.product_id.volume or 0.0) * quantities
            quantity += quantities
        total = (order.amount_total or 0.0) - total_delivery

        return self.get_price_from_picking(total, weight, volume, quantity)

    @api.multi
    def get_price_from_picking(self, total, weight, volume, quantity):
        price = 0.0
        ok = False
        price_dict = {'price': total, 'volume': volume, 'weight': weight, 'wv': volume * weight, 'quantity': quantity}
        for grid in self:
            for line in grid.line_ids:
                test = eval(line.variable + line.operator + str(line.max_value), price_dict)
                if test:
                    if line.price_type == 'variable':
                        price = line.list_price * price_dict[line.variable_factor]
                    else:
                        price = line.list_price
                    ok = True
                    break
        if not ok:
            raise UserError(_("Selected product in the delivery method doesn't fulfill any of the delivery grid(s) criteria."))
        return price


class DeliveryGridLine(models.Model):
    _name = "delivery.grid.line"
    _description = "Delivery Grid Line"
    _order = 'sequence, list_price'

    name = fields.Char(required=True)
    sequence = fields.Integer(required=True, help="Gives the sequence order when calculating delivery grid.", default=10)
    grid_id = fields.Many2one('delivery.grid', string='Grid', required=True, ondelete='cascade')
    variable = fields.Selection([('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'), ('quantity', 'Quantity')], required=True, default="weight", oldname='type')
    operator = fields.Selection([('==', '='), ('<=', '<='), ('<', '<'), ('>=', '>='), ('>', '>')], required=True, default="<=")
    max_value = fields.Float(string='Maximum Value', required=True)
    price_type = fields.Selection([('fixed', 'Fixed'), ('variable', 'Variable')], required=True, default="fixed")
    variable_factor = fields.Selection([('weight', 'Weight'), ('volume', 'Volume'), ('wv', 'Weight * Volume'), ('price', 'Price'), ('quantity', 'Quantity')], required=True, default="weight")
    list_price = fields.Float(string='Sale Price', digits_compute=dp.get_precision('Product Price'), required=True)
    standard_price = fields.Float(string='Cost Price', digits_compute= dp.get_precision('Product Price'), required=True)
