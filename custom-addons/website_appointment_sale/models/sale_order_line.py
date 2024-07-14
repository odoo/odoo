# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    calendar_booking_ids = fields.One2many("calendar.booking", "order_line_id", "Bookings")
    calendar_event_id = fields.Many2one("calendar.event", "Meeting")

    @api.depends('calendar_booking_ids')
    def _compute_product_uom_readonly(self):
        booking_so_lines = self.filtered("calendar_booking_ids")
        booking_so_lines.product_uom_readonly = True
        super(SaleOrderLine, self - booking_so_lines)._compute_product_uom_readonly()

    def _is_not_sellable_line(self):
        return super()._is_not_sellable_line() or self.calendar_booking_ids

    def unlink(self):
        """ Manually unlink in order to unlink answer inputs linked to calendar bookings. """
        self.calendar_booking_ids.unlink()
        return super().unlink()
