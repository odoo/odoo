# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBoothSlot(models.Model):
    _inherit = 'event.booth.slot'

    partner_id = fields.Many2one(related='sale_order_id.partner_id', string='Rented By')
    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', ondelete='set null',
        readonly=True, states={'available': [('readonly', False)]})
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Sales Order Line', ondelete='set null',
        readonly=True, states={'available': [('readonly', False)]})

    def _get_booth_multiline_description(self):
        return '%s - %s\n%s' % (
            self.event_booth_id.name,
            self._get_duration_display(),
            self.event_id.display_name
        )

    def action_view_sale_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    def action_confirm(self, registration_id):
        super(EventBoothSlot, self).action_confirm(registration_id)
        self.write({
            'sale_order_id': registration_id.sale_order_id.id,
            'sale_order_line_id': registration_id.sale_order_line_id.id,
        })
