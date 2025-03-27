# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Techno Solutions (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class SaleOrder(models.Model):
    """
       Inherits the Sale Order model to add the ability to apply stock
       reservation for products in draft state. This model also adds a state for
       tracking the reservation status and a one-to-many relationship to the
       Stock Reserved model for storing the details of the reserved stock.
       """
    _inherit = "sale.order"

    apply_stock_reservation = fields.Boolean(
        string="Apply stock reservation",
        help="Apply stock reservation in draft")
    state_reservation = fields.Selection([
        ('reserved', 'Reserved'), ('cancel', 'Cancelled')],
        help="Condition for visibility of buttons")
    reserved_stock_ids = fields.One2many(
        "stock.reserved",
        "sale_order_id",
        string="Reserved Stock",
        help="Stock reserved details")

    def action_create_stock_reservation(self):
        """
          This function creates a stock reservation based on the current sale
          order's order lines.
          If the sale order has order lines, the function creates a list of
          tuples representing the order lines,which are used to set default
          values for the stock reservation. Each tuple contains three elements:
          (0, 0, {...}), where the dictionary contains values for the following
          fields of the stock reservation:

          - order_line_name: a string representing the name of the sale order
            and the order line, concatenated
          - product_id: the ID of the product being reserved
          - quantity: the quantity being reserved, in the unit of measure
            specified by the order line
          - unit_of_measure_id: the ID of the unit of measure being used for the
           reservation
          - reserve_quantity: the quantity being reserved, in the unit of
          measure specified by the product

          If the sale order does not have any order lines, an empty list
          created.

          The function then returns a dictionary representing an action to
          create a new stock reservation.
          The dictionary has the following keys:

          - name: a string representing the name of the action
          - type: a string representing the type of the action (in this case,
           'ir.actions.act_window')
          - view_type: a string representing the type of view to use
            (in this case, 'form')
          - view_mode: a string representing the mode of the view
            (in this case, 'form')
          - res_model: a string representing the name of the model being used
            (in this case,'sale.stock.reservation')
          - context: a dictionary representing the context to use when creating
            the stock reservation
          - default_sale_order_id: the ID of the sale order being used as the
            basis for the reservation
          - default_stock_reservation_ids: the list of tuples representing the
            order lines (or an empty list)
          - view_id: the ID of the view to use (retrieved using self.env.ref())
          - target: a string representing the target for the action
            (in this case, 'new')

          :return: a dictionary representing the action to create a new stock
           reservation
          """
        line_vals = [(0, 0, {
            'order_line_name': f"{self.name}-{line.name}",
            'product_id': line.product_id.id,
            'quantity': line.product_uom_qty,
            'unit_of_measure_id': line.product_uom.id,
            'reserve_quantity': line.product_uom_qty
        }) for line in self.order_line] if self.order_line else []
        return {
            'name': "Stock Reservation",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.stock.reservation',
            'context': {'default_sale_order_id': self.id,
                        'default_stock_reservation_ids': line_vals},
            'view_id': self.env.ref(
                'sales_stock_reservation.sale_stock_reservation_view_form').id,
            'target': 'new',
        }

    def action_cancel_reservation(self):
        """
        This function cancels a stock reservation by setting its state to
         'cancel', cancelling the moves associated with the reservation's
          reserved stock,and setting the status of the reserved stock to
         'cancelled'.

        The function first sets the `state_reservation` field of the current
        object to 'cancel'.

        It then retrieves the `move_id` field of each reserved stock associated
        with the reservation using `mapped()`,and calls the `_action_cancel()`
        method on the resulting recordset to cancel the moves.

        After cancelling the moves, the function sets the `status` field of each
        reserved stock associated with the reservation to 'cancelled' using
        `mapped()`.

        Finally, the function returns True to indicate that the cancellation
        was successful.

        :return: True if the reservation was successfully cancelled, False
        otherwise
        """
        self.state_reservation = 'cancel'
        self.reserved_stock_ids.mapped('move_id')._action_cancel()
        self.mapped("reserved_stock_ids").status = 'cancelled'
        return True

    def action_confirm(self):
        """
        This function confirms a sale order by calling the parent
        `action_confirm()` method and then cancelling any associated stock
         reservation.
        The function first calls the `super()` method to confirm the sale order
         using the parent implementation.
        It then calls the `cancel_reservation()` method to cancel any existing
         stock reservation associated with the sale order.
        Finally, the function returns the result of the `super()` method call to
         indicate whether the sale order was successfully confirmed.

        :return: the result of the parent `action_confirm()` method call
        """
        res = super().action_confirm()
        self.action_cancel_reservation()
        return res
