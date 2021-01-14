# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventBooth(models.Model):
    _name = 'event.booth'
    _description = 'Event Booth'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    event_id = fields.Many2one(
        'event.event', string='Event', required=True)
    booth_category_id = fields.Many2one(
        'event.booth.category', string='Booth Category',
        domain="[('event_id', '=', event_id)]", required=True)
    is_multi_slots = fields.Boolean(
        string='Multi Slots', related='booth_category_id.is_multi_slots')
    state = fields.Selection([
        ('available', 'Available'),
        ('unavailable', 'Unavailable')
     ], string='Status', compute='_compute_state', store=True, group_expand='_group_expand_states',
        help='Shows the availability of a Booth, available until all his slots are taken')
    booth_slot_ids = fields.One2many('event.booth.slot', 'event_booth_id', string='Slots')
    booth_slot_count = fields.Integer(string='Total Slots', store=True,
                                      compute='_compute_booth_slot_count')
    booth_slot_count_available = fields.Integer(string='Available Slots', store=True,
                                                compute='_compute_booth_slot_count')

    @api.depends('booth_slot_ids.state')
    def _compute_state(self):
        for booth in self:
            if booth.booth_slot_ids and any(slot.state == 'available' for slot in booth.booth_slot_ids):
                booth.state = 'available'
            else:
                booth.state = 'unavailable'

    @api.depends('booth_slot_ids', 'booth_slot_ids.state')
    def _compute_booth_slot_count(self):
        booth_slots = self.env['event.booth.slot'].sudo().read_group(
            [('event_booth_id', 'in', self.ids)],
            ['event_booth_id', 'state'], ['event_booth_id', 'state'], lazy=False
        )
        booths_slot_available_count = dict()
        booths_slot_total_count = dict()
        for booth_slot in booth_slots:
            booth_id = booth_slot['event_booth_id'][0]
            if booth_slot['state'] == 'available':
                booths_slot_available_count[booth_id] = booth_slot['__count']
            booths_slot_total_count.setdefault(booth_id, 0)
            booths_slot_total_count[booth_id] += booth_slot['__count']

        for booth in self:
            booth.booth_slot_count_available = booths_slot_available_count.get(booth.id, 0)
            booth.booth_slot_count = booths_slot_total_count.get(booth.id, 0)

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.model_create_multi
    def create(self, vals_list):
        """If 'is_multi_slots' is not set an unique slot will be created for the duration of the event"""
        booths = super(EventBooth, self).create(vals_list)
        slots_list = [{
            'event_booth_id': booth.id,
            'booking_from': booth.event_id.date_begin,
            'booking_to': booth.event_id.date_end} for booth in booths if not booth.is_multi_slots]
        if slots_list:
            self.env['event.booth.slot'].create(slots_list)
        return booths
