# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RentalProcessing(models.TransientModel):
    _inherit = 'rental.order.wizard'

    has_tracked_lines = fields.Boolean(
        string="Has lines with tracked products", compute='_compute_has_tracked_lines')

    has_lines_missing_stock = fields.Boolean(
        string="Has lines whose products have insufficient stock", compute="_compute_has_lines_missing_stock")

    @api.depends('rental_wizard_line_ids')
    def _compute_has_tracked_lines(self):
        for wizard in self:
            wizard.has_tracked_lines = any(line.tracking == 'serial' for line in wizard.rental_wizard_line_ids)

    @api.depends('rental_wizard_line_ids.qty_delivered')
    def _compute_has_lines_missing_stock(self):
        for wizard in self:
            wizard.has_lines_missing_stock = any(line.is_product_storable and line.status == 'pickup' and line.qty_delivered > line.qty_available for line in wizard.rental_wizard_line_ids)


class RentalProcessingLine(models.TransientModel):
    _inherit = 'rental.order.wizard.line'

    def _default_wizard_line_vals(self, line, status):
        default_line_vals = super(RentalProcessingLine, self)._default_wizard_line_vals(line, status)

        default_line_vals.update({
            'tracking': line.product_id.tracking,
        })

        pickeable_lots = self.env['stock.lot']
        returnable_lots = self.env['stock.lot']
        reserved_lots = line.reserved_lot_ids
        pickedup_lots = line.pickedup_lot_ids
        returned_lots = line.returned_lot_ids

        if status == 'pickup':
            if line.product_id.tracking == 'serial':
                # If product is tracked by serial numbers
                # Get lots in stock:
                rentable_lots = self.env['stock.lot']._get_available_lots(line.product_id, line.order_id.warehouse_id.lot_stock_id)
                # Get lots reserved/pickedup and not already returned
                rented_lots = line.product_id._get_unavailable_lots(
                    fields.Datetime.now(),
                    line.return_date,
                    ignored_soline_id=line.id,
                    warehouse_id=line.order_id.warehouse_id.id)

                # Don't show reserved lots if they aren't back (or were moved by another app)
                if pickedup_lots:
                    # As we ignored current SaleOrderLine for availability, we need to add
                    # its pickedup_lots to the rented ones to make sure it cannot be picked-up twice.
                    rented_lots += pickedup_lots

                if returned_lots:
                    """As returned lots are considered available, in case of partial pickup+return
                    We could pickup X, return X and then X would always be available for pickup
                    As this would bring problems of quantities and other unexpected behavior
                    We consider that returned serial numbers cannot be picked up again
                    for the same order_line."""
                    rented_lots += returned_lots

                pickeable_lots = rentable_lots - rented_lots

                # Don't count
                # * unavailable lots
                # * lots expected to go to another client before
                # as reserved lots (which will be auto-filled as pickedup_lots).
                reserved_lots = reserved_lots & pickeable_lots
                default_line_vals.update({
                    'qty_delivered': len(reserved_lots),
                })

            if line.product_id.type == 'product':
                default_line_vals.update({
                    'qty_available': line.product_id.with_context(
                        from_date=max(line.reservation_begin, fields.Datetime.now()),
                        to_date=line.return_date,
                        warehouse_id=line.order_id.warehouse_id.id).qty_available,
                    'is_product_storable': True
                })
                # On pickup: only show quantity currently available
                # because the unavailable qty is in company_id.rental_loc_id.

            default_line_vals.update({
                'pickedup_lot_ids': [(6, 0, reserved_lots.ids)],
                'returned_lot_ids': [(6, 0, returned_lots.ids)],
                'pickeable_lot_ids': [(6, 0, pickeable_lots.ids)],
                'returnable_lot_ids': [(6, 0, returnable_lots.ids)]
            })
        elif status == 'return':
            returnable_lots = pickedup_lots - returned_lots
            default_line_vals.update({
                'pickedup_lot_ids': [(6, 0, pickedup_lots.ids)],
                'returned_lot_ids': [(6, 0, returnable_lots.ids)],
                'pickeable_lot_ids': [(6, 0, pickeable_lots.ids)],
                'returnable_lot_ids': [(6, 0, returnable_lots.ids)]
            })

        return default_line_vals

    qty_available = fields.Float(string="Available", default=0.0)
    is_product_storable = fields.Boolean(compute="_compute_is_product_storable")

    tracking = fields.Selection(related='product_id.tracking')

    pickeable_lot_ids = fields.Many2many(
        'stock.lot', 'wizard_pickeable_serial', store=False)
    returnable_lot_ids = fields.Many2many(
        'stock.lot', 'wizard_returnable_serial', store=False)
    pickedup_lot_ids = fields.Many2many(
        'stock.lot', 'wizard_pickedup_serial',
        domain="[('id', 'in', pickeable_lot_ids)]")
    returned_lot_ids = fields.Many2many(
        'stock.lot', 'wizard_returned_serial',
        domain="[('id', 'in', returnable_lot_ids)]")

    @api.depends('product_id')
    def _compute_is_product_storable(self):
        """Product type ?= storable product."""
        for line in self:
            line.is_product_storable = line.product_id and line.product_id.type == "product"

    @api.onchange('pickedup_lot_ids')
    def _onchange_pickedup_lot_ids(self):
        self.qty_delivered = len(self.pickedup_lot_ids)

    @api.onchange('returned_lot_ids')
    def _onchange_returned_lot_ids(self):
        self.qty_returned = len(self.returned_lot_ids)

    @api.constrains('pickedup_lot_ids', 'qty_delivered')
    def _is_pickup_tracking_fulfilled(self):
        for wizard_line in self:
            if wizard_line.status == 'pickup' and wizard_line.tracking == 'serial':
                if wizard_line.qty_delivered != len(wizard_line.pickedup_lot_ids):
                    raise ValidationError(_("Please specify the serial numbers picked up for the tracked products."))

    @api.constrains('returned_lot_ids', 'qty_returned')
    def _is_return_tracking_fulfilled(self):
        for wizard_line in self:
            if wizard_line.status == 'return' and wizard_line.tracking == 'serial':
                if wizard_line.qty_returned != len(wizard_line.returned_lot_ids):
                    raise ValidationError(_("Please specify the serial numbers returned for the tracked products."))

    def _apply(self):
        serial_lines = self.filtered(lambda line: line.tracking == 'serial')

        # First, we deduct from the wizard the lots already picked up/returned
        for line in serial_lines:
            sol = line.order_line_id
            if line.status == 'pickup':
                pickedup_lot_ids = line.pickedup_lot_ids - sol.pickedup_lot_ids
                line.write({
                    'qty_delivered': len(pickedup_lot_ids),
                    'pickedup_lot_ids': [(6, 0, pickedup_lot_ids.ids)],
                })
            elif line.status == 'return':
                returned_lot_ids = line.returned_lot_ids - sol.returned_lot_ids
                line.write({
                    'qty_returned': len(returned_lot_ids),
                    'returned_lot_ids': [(6, 0, returned_lot_ids.ids)],
                })

        msg = super()._apply()
        for line in serial_lines:
            sol = line.order_line_id
            if line.status == 'pickup':
                sol.pickedup_lot_ids |= line.pickedup_lot_ids
            elif line.status == 'return':
                sol.returned_lot_ids |= line.returned_lot_ids
        return msg

    def _generate_log_message(self):
        """Override"""
        msg = ""
        for line in self:
            order_line = line.order_line_id
            diff, old_qty, new_qty = line._get_diff()
            if diff:  # i.e. diff>0

                msg += Markup("<li> %s") % (order_line.product_id.display_name)

                if old_qty > 0:
                    msg += Markup(": %s -> <b> %s </b> %s ") % (old_qty, new_qty, order_line.product_uom.name)
                elif new_qty != 1 or order_line.product_uom_qty > 1.0:
                    msg += ": %s %s " % (new_qty, order_line.product_uom.name)
                # If qty = 1, product has been picked up, no need to specify quantity
                # But if ordered_qty > 1.0: we need to still specify pickedup/returned qty

                if line.status == 'pickup' and line.pickedup_lot_ids:
                    msg += ": " + ', '.join(line.pickedup_lot_ids.mapped('name'))
                elif line.status == 'return' and line.returned_lot_ids:
                    msg += ": " + ', '.join(line.returned_lot_ids.mapped('name'))

                msg += Markup("<br/>")
        return msg
