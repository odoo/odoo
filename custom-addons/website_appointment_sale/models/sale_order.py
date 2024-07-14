# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    calendar_event_count = fields.Integer('Meetings', compute='_compute_meeting_count')

    @api.depends('order_line')
    def _compute_meeting_count(self):
        event_count_per_so = {
            sale_order.id: event_count
            for sale_order, event_count in self.env['sale.order.line']._read_group(
                [('order_id', 'in', self.ids), ('calendar_event_id', '!=', False)],
                ['order_id'],
                ['__count']
            )
        }
        for sale_order in self:
            sale_order.calendar_event_count = event_count_per_so.get(sale_order.id, 0)

    def action_view_calendar_events(self):
        action = self.env['ir.actions.act_window']._for_xml_id('calendar.action_calendar_event')
        action['domain'] = [('id', 'in', self.order_line.calendar_event_id.ids)]
        action['views'] = [(False, 'tree'), (False, 'form')]
        action['context'] = {'active_test': False}
        return action

    def _action_cancel(self):
        self.order_line.calendar_event_id.action_archive()
        return super()._action_cancel()

    def _action_confirm(self):
        """ Override: as this method is called when successfully paying the SO, or manually in back-end,
            we consider that the linked bookings can be transformed to a calendar event """
        self.order_line.calendar_event_id.action_unarchive()
        self.order_line.calendar_booking_ids._make_event_from_paid_booking()
        return super()._action_confirm()

    def _check_cart_is_ready_to_be_paid(self):
        self.ensure_one()
        bookings = self.order_line.calendar_booking_ids
        unavailable_bookings = bookings._filter_unavailable_bookings()
        if unavailable_bookings:
            raise ValidationError(_(
                "The following bookings are not available anymore during the selected period"
                " and your cart must be updated. We are sorry for the inconvenience."
            ) + '\n\n' + ', '.join(
                [booking._get_description() for booking in unavailable_bookings]
            ))
        return super()._check_cart_is_ready_to_be_paid()

    def _cart_find_product_line(self, product_id=None, line_id=None, calendar_booking_id=False, **kwargs):
        """ Avoid returning the lines in case of an appointment if the same product exists in
            the cart, as one could take many different slots from the same appointment, or even from
            different appointments with the same booking_fees product. One line per booking, with a
            unique description, is meant to be in this case. """
        if calendar_booking_id:
            return self.env['sale.order.line']
        return super()._cart_find_product_line(product_id, line_id, **kwargs)

    def _verify_updated_quantity(self, order_line, product_id, new_qty, **kwargs):
        """ Forbid quantity updates on lines with calendar bookings, and total cart quantities
            going over available resources / users. """
        product = self.env['product.product'].browse(product_id)
        if product.detailed_type == 'booking_fees' and new_qty > 1:
            return 1, _('You cannot manually change the quantity of a Booking Fees product.')
        return super()._verify_updated_quantity(order_line, product_id, new_qty, **kwargs)

    def _prepare_order_line_values(self, product_id, quantity, calendar_booking_id=False, calendar_booking_tz=False, **kwargs):
        """ Add calendar booking values to the SOL creation values (if a booking id is provided). """
        values = super()._prepare_order_line_values(product_id, quantity, **kwargs)
        if not calendar_booking_id:
            return values
        booking_sudo = self.env['calendar.booking'].sudo().browse(calendar_booking_id)
        values['calendar_booking_ids'] = [Command.link(calendar_booking_id)]
        # Using partner's lang, same as usual behavior in _compute_name.
        # It is linked to partner created / linked on appointment form submission.
        values['name'] = booking_sudo.with_context(tz=calendar_booking_tz, lang=self.partner_id.lang)._get_description()
        return values

    def unlink(self):
        """ Manually unlink in order to unlink answer inputs linked to calendar bookings. """
        self.order_line.unlink()
        return super().unlink()
