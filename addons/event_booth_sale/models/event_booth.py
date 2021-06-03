# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventBooth(models.Model):
    _inherit = 'event.booth'

    # registrations
    event_booth_registration_ids = fields.One2many('event.booth.registration', 'event_booth_id')
    # sale information
    so_registration_line_ids = fields.Many2many(
        'sale.order.line', 'event_booth_registration',
        'event_booth_id', 'sale_order_line_id', string='SO Lines with reservations')
    sale_order_id = fields.Many2one(related='sale_order_line_id.order_id', store='True')
    sale_order_line_id = fields.Many2one(
        'sale.order.line', string='Final Sale Order Line', ondelete='set null',
        readonly=True, states={'available': [('readonly', False)]})
    is_paid = fields.Boolean('Is Paid')

    def _get_booth_multiline_description(self):
        return '%s : \n%s' % (
            self.event_id.display_name,
            '\n'.join(['- %s' % booth.name for booth in self])
        )

    def action_view_sale_order(self):
        self.sale_order_id.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('sale.action_orders')
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action
