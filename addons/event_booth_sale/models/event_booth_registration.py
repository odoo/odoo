# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBoothRegistration(models.Model):
    _name = 'event.booth.registration'
    _description = 'Event Booth Registration'

    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', required=True)
    event_booth_id = fields.Many2one('event.booth', string='Booth', required=True)

    def action_confirm(self):
        booth_ids = self.mapped('event_booth_id')
        booth_ids.action_confirm({
            'sale_order_line_id': self.sale_order_line_id,
            'is_paid': True,
        })
        registration_to_remove = self.search([
            ('event_booth_id', 'in', booth_ids.ids)
        ]) - self
        registration_to_remove._cancel_pending_registrations()

    def _cancel_pending_registrations(self):
        for order in self.mapped('sale_order_line_id').mapped('order_id'):
            order.message_notify(
                body='<p>Booths Sold, next time be faster !</p>',
                partner_ids=[order.partner_id.id],
                subtype_xmlid='mail.mt_comment',
                email_layout_xmlid='mail.mail_notification_light',
            )
            order.action_cancel()
        self.unlink()
