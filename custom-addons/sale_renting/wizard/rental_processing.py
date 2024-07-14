# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RentalProcessing(models.TransientModel):
    _name = 'rental.order.wizard'
    _description = "Pick-up/Return products"

    order_id = fields.Many2one('sale.order', required=True, ondelete='cascade')
    rental_wizard_line_ids = fields.One2many('rental.order.wizard.line', 'rental_order_wizard_id')
    status = fields.Selection(
        selection=[
            ('pickup', 'Pickup'),
            ('return', 'Return'),
        ],
    )
    is_late = fields.Boolean(related='order_id.is_late')

    @api.onchange('order_id')
    def _get_wizard_lines(self):
        """Use Wizard lines to set by default the pickup/return value
        to the total pickup/return value expected"""
        rental_lines_ids = self.env.context.get('order_line_ids', [])
        rental_lines_to_process = self.env['sale.order.line'].browse(rental_lines_ids)

        # generate line values
        if rental_lines_to_process:
            lines_values = []
            for line in rental_lines_to_process:
                lines_values.append(self.env['rental.order.wizard.line']._default_wizard_line_vals(line, self.status))

            self.rental_wizard_line_ids = [(6, 0, [])] + [(0, 0, vals) for vals in lines_values]

    def apply(self):
        """Apply the wizard modifications to the SaleOrderLine(s).

        And logs the rental infos in the SaleOrder chatter
        """
        for wizard in self:
            msg = wizard.rental_wizard_line_ids._apply()
            if msg:
                for key, value in wizard._fields['status']._description_selection(wizard.env):
                    if key == wizard.status:
                        translated_status = value
                        break

                msg = Markup("<b>%s</b>:<ul>%s</ul>") % (translated_status, msg)
                wizard.order_id.message_post(body=msg)
        return  # {'type': 'ir.actions.act_window_close'}


class RentalProcessingLine(models.TransientModel):
    _name = 'rental.order.wizard.line'
    _description = "RentalOrderLine transient representation"

    @api.model
    def _default_wizard_line_vals(self, line, status):
        return {
            'order_line_id': line.id,
            'product_id': line.product_id.id,
            'qty_reserved': line.product_uom_qty,
            'qty_delivered': line.qty_delivered if status == 'return' else line.product_uom_qty - line.qty_delivered,
            'qty_returned': line.qty_returned if status == 'pickup' else line.qty_delivered - line.qty_returned,
        }

    rental_order_wizard_id = fields.Many2one('rental.order.wizard', 'Rental Order Wizard', required=True, ondelete='cascade')
    status = fields.Selection(related='rental_order_wizard_id.status')

    order_line_id = fields.Many2one('sale.order.line', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    qty_reserved = fields.Float("Reserved")
    qty_delivered = fields.Float("Picked-up")
    qty_returned = fields.Float("Returned")

    @api.constrains('qty_returned', 'qty_delivered')
    def _only_pickedup_can_be_returned(self):
        for wizard_line in self:
            if wizard_line.status == 'return' and wizard_line.qty_returned > wizard_line.qty_delivered:
                raise ValidationError(_("You can't return more than what's been picked-up."))

    def _apply(self):
        """Apply the wizard modifications to the SaleOrderLine.

        :return: message to log on the Sales Order.
        :rtype: str
        """
        msg = self._generate_log_message()
        for wizard_line in self:
            order_line = wizard_line.order_line_id
            if wizard_line.status == 'pickup' and wizard_line.qty_delivered > 0:
                delivered_qty = order_line.qty_delivered + wizard_line.qty_delivered
                vals = {'qty_delivered': delivered_qty}
                if delivered_qty > order_line.product_uom_qty:
                    vals['product_uom_qty'] = delivered_qty
                order_line.update(vals)

            elif wizard_line.status == 'return' and wizard_line.qty_returned > 0:
                if wizard_line.rental_order_wizard_id.is_late:
                    # Delays facturation
                    order_line._generate_delay_line(wizard_line.qty_returned)

                order_line.update({
                    'qty_returned': order_line.qty_returned + wizard_line.qty_returned
                })
        return msg

    def _get_diff(self):
        """Return the quantity changes due to the wizard line.

        :return: (diff, old_qty, new_qty) floats
        :rtype: tuple(float, float, float)
        """
        self.ensure_one()
        order_line = self.order_line_id
        if self.status == 'pickup':
            return self.qty_delivered, order_line.qty_delivered, order_line.qty_delivered + self.qty_delivered
        else:
            return self.qty_returned, order_line.qty_returned, order_line.qty_returned + self.qty_returned

    def _generate_log_message(self):
        msg = ""
        for line in self:
            order_line = line.order_line_id
            diff, old_qty, new_qty = line._get_diff()
            if diff:  # i.e. diff>0

                msg += Markup("<li> %s") % (order_line.product_id.display_name)

                if old_qty > 0:
                    msg += Markup(": %s -> <b> %s </b> %s <br/>") % (old_qty, new_qty, order_line.product_uom.name)
                elif new_qty != 1 or order_line.product_uom_qty > 1.0:
                    msg += Markup(": %s %s <br/>") % (new_qty, order_line.product_uom.name)
                # If qty = 1, product has been picked up, no need to specify quantity
                # But if ordered_qty > 1.0: we need to still specify pickedup/returned qty
        return msg
