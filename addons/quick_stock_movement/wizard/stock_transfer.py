# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockTransfer(models.TransientModel):
    _name = 'stock.transfer'
    _description = "Stock Transfer"
    """Model for stock Transfer"""

    product_id = fields.Many2one('product.template', string='Product', help='Product Details')
    qty_available = fields.Float(string='Available Quantity',
                                 help="Available quantity of the product.",
                                 related="product_id.qty_available")
    qty_to_move = fields.Float(string='Quantity to Move', help="Quantity to move")

    def _get_location(self):
        """To get locations"""
        location = self.env['stock.location'].search(
            [('usage', '=', 'internal')])
        return [(4, loc) for loc in location.ids]

    location_ids = fields.Many2many('stock.location', string='Locations', help="Locations")
    source_location_id = fields.Many2one('stock.location',
                                         domain="[('id', 'in', location_ids)]",
                                         required=True,
                                         string='Source location',
                                         help='Source Location Details')
    destination_location_id = fields.Many2one('stock.location',
                                              domain=
                                              "[('usage', '=', 'internal')]",
                                              required=True,
                                              string='Destination location',
                                              help='Destination '
                                                   'Location Details')

    @api.onchange('product_id')
    def _onchange_product(self):
        """To get the Current Product Location """
        for rec in self:
            if rec.product_id:
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', self.product_id.product_variant_id.id),
                     ('on_hand', '=', True)])
                location = stock_quant.mapped('location_id')
                rec.location_ids = [(4, loc) for loc in location.ids]

    def create_action(self):
        """Create stock transfer"""
        if self.qty_to_move > self.qty_available:
            raise UserError(_('Quanty to move must be less '
                            'than or equal to available quantity'))
        else:
            operation_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', self.source_location_id.warehouse_id.id)])
            if not operation_type:
                raise UserError(_('No operation type for this transfer'))
            else:
                stock_quant = self.env['stock.quant'].search(
                    [('product_id', '=', self.product_id.product_variant_id.id),
                     ('on_hand', '=', True)])
                for rec in stock_quant:
                    if rec.quantity >= self.qty_to_move:
                        location = stock_quant.mapped('location_id')
                        if self.source_location_id in location:
                            stock_picking_vals = {
                                'picking_type_id': operation_type.id,
                                'location_id': self.source_location_id.id,
                                'location_dest_id':
                                    self.destination_location_id.id,
                                'scheduled_date': fields.Datetime.now(),
                            }
                            stock_picking = self.env['stock.picking'].\
                                sudo().create(stock_picking_vals)
                            stock_move_vals = {
                                'name': self.product_id.name,
                                'product_id':
                                    self.product_id.product_variant_id.id,
                                'location_id':
                                    self.source_location_id.id,
                                'location_dest_id':
                                    self.destination_location_id.id,
                                'product_uom_qty': self.qty_to_move,
                                'picking_id': stock_picking.id
                            }
                            self.env['stock.move'].sudo().\
                                create(stock_move_vals)
                            stock_picking.action_confirm()
                            stock_picking.sudo().button_validate()
                            return {
                                'type': 'ir.actions.act_window',
                                'target': 'current',
                                'name': "Stock Transfer",
                                'view_mode': 'form',
                                'res_model': 'stock.picking',
                                'res_id': stock_picking.id
                                }
                        else:
                            raise UserError(_(
                                'No available Quantity for this Product.'))
                    else:
                        raise UserError(_('No available Quantity '
                                        'for this Product.'))
