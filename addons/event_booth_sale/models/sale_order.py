# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    event_booth_slot_ids = fields.One2many('event.booth.slot', 'sale_order_id', string='Slots')
    event_booth_slot_count = fields.Integer(string='Slot Count', compute='_compute_event_booth_slot_count')

    @api.depends('event_booth_slot_ids')
    def _compute_event_booth_slot_count(self):
        slot_data = self.env['event.booth.slot'].read_group(
            [('sale_order_id', 'in', self.ids)],
            ['sale_order_id'], ['sale_order_id']
        )
        slot_mapped = dict((data['sale_order_id'][0], data['sale_order_id_count']) for data in slot_data)
        for so in self:
            so.event_booth_slot_count = slot_mapped.get(so.id, 0)

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for so in self:
            so.order_line._update_booth_slot()
            if any(line.is_event_booth for line in so.order_line):
                return self.env['ir.actions.act_window']\
                    .with_context(default_sale_order_id=so.id)\
                    ._for_xml_id('event_booth_sale.event_booth_slot_edit_action')
        return res

    def action_view_booth_list(self):
        action = self.env['ir.actions.act_window']._for_xml_id('event_booth.event_booth_slot_action')
        action['domain'] = [('sale_order_id', 'in', self.ids)]
        return action
