# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class UpdateQtyWizard(models.TransientModel):
    _name = 'update.qty.wizard'
    _description = 'Update Quantity Wizard'

    picking_id = fields.Many2one('stock.picking', string='Picking Order')
    license_plate_id = fields.Many2one('license.plate.orders', string='License Plate', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity', required=True)

    @api.model
    def default_get(self, fields_list):
        """
        This method sets default values for picking_id and license_plate_id.
        """
        res = super(UpdateQtyWizard, self).default_get(fields_list)
        if self._context.get('default_license_plate_orders_line_id'):
            line = self.env['license.plate.orders.line'].browse(self._context['default_license_plate_orders_line_id'])
            res.update({
                'picking_id': line.license_plate_orders_id.picking_id.id,
                'license_plate_id': line.license_plate_orders_id.id,
                'product_id': line.product_id.id,
            })
        return res

    def update_qty(self):
        """
        This method updates the quantity on the license plate order line.
        It calculates the difference between the current quantity and the new quantity.
        If the difference is positive, it checks if the stock move has enough remaining quantity.
        Then, it updates both the license plate line and the stock move accordingly.
        """
        line_id = self.env.context.get('default_license_plate_orders_line_id')
        line = self.env['license.plate.orders.line'].browse(line_id)

        # Fetch the stock move line related to this product and picking
        stock_move = self.env['stock.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('product_id', '=', self.product_id.id)
        ], limit=1)

        if not stock_move:
            raise ValidationError(_("No stock move found for the product '%s' in the selected picking.")
                                  % (self.product_id.display_name))

        # Calculate the remaining quantity from the stock move line
        stock_remaining_qty = stock_move.remaining_qty

        # Calculate the difference between new quantity and current line quantity
        qty_difference = self.quantity - line.quantity

        # If the user is increasing the quantity (difference > 0)
        if qty_difference > 0:
            # Check if the stock move can fulfill the additional quantity
            if qty_difference > stock_remaining_qty:
                raise ValidationError(
                    _("The additional quantity exceeds the available remaining quantity in the stock move.")
                )
            # Subtract the additional quantity from the stock move's remaining quantity
            stock_move.remaining_qty -= qty_difference

        # If the user is decreasing the quantity (difference < 0)
        elif qty_difference < 0:
            # Add the reduced quantity back to the stock move's remaining quantity
            stock_move.remaining_qty += abs(qty_difference)

        # Update the quantity on the license plate order line
        line.quantity = self.quantity
        stock_move._compute_delivery_receipt_state()
        # Optionally, update the is_remaining_qty flag on the stock move if needed

        return {'type': 'ir.actions.act_window_close'}



