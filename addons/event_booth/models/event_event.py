# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo import Command


class Event(models.Model):
    _inherit = 'event.event'

    event_booth_category_ids = fields.One2many(
        'event.booth.category', 'event_id', string='Booth Category',
        compute='_compute_event_booth_category_ids', readonly=False, store=True)
    event_booth_ids = fields.One2many(
        'event.booth', 'event_id', string='Booths')
    event_booth_count = fields.Integer(
        string='Total Booths',
        compute='_compute_event_booth_count')
    event_booth_count_available = fields.Integer(
        string='Available Booths',
        compute='_compute_event_booth_count')
    event_booth_slot_ids = fields.One2many(
        'event.booth.slot', 'event_id', string='Slots')
    event_booth_slot_count = fields.Integer(
        string='Total Slots',
        compute='_compute_event_booth_slots_count')
    event_booth_slot_count_available = fields.Integer(
        string='Available Slots',
        compute='_compute_event_booth_slots_count')

    @api.depends('event_type_id')
    def _compute_event_booth_category_ids(self):
        """
        When setting the event template to one with the 'use_booth' option set :
            - If there is no event.booth.category it will copy those on the event template
            - If there are one or more event.booth.category it will copy the missing ones
        When setting the event template to one without the 'use booth' option set :
            - It will keep the event.booth.category with already created event.booth and
            delete the empty ones.
        """
        if self.ids or self._origin.ids:
            booth_tokeep_ids = self.env['event.booth.category'].search([
                ('event_id', 'in', self.ids or self._origin.ids),
                ('event_booth_ids', '!=', False),
            ]).ids
        else:
            booth_tokeep_ids = []
        for event in self:
            if booth_tokeep_ids:
                booth_toremove_ids = event._origin.event_booth_category_ids.filtered(lambda booth: booth.id not in booth_tokeep_ids)
                command = [Command.unlink(booth.id) for booth in booth_toremove_ids]
            else:
                command = [Command.clear()]
            if event.event_type_id.use_booth:
                booth_category_fields = self.env['event.booth.category']._get_event_booth_category_fields_whitelist()
                command += [
                    Command.create({
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel)
                        else line[attribute_name].id for attribute_name in booth_category_fields
                    }) for line in event.event_type_id.event_type_booth_category_ids if line.name not in event.event_booth_category_ids.mapped('name')
                ]
            event.event_booth_category_ids = command

    def _get_booth_stat_count(self, model):
        elements = self.env[model].sudo().read_group(
            [('event_id', 'in', self.ids)],
            ['event_id', 'state'], ['event_id', 'state'], lazy=False
        )
        elements_total_count = dict()
        elements_available_count = dict()
        for element in elements:
            event_id = element['event_id'][0]
            if element['state'] == 'available':
                elements_available_count[event_id] = element['__count']
            elements_total_count.setdefault(event_id, 0)
            elements_total_count[event_id] += element['__count']
        return elements_available_count, elements_total_count

    @api.depends('event_booth_ids', 'event_booth_ids.state')
    def _compute_event_booth_count(self):
        booths_available_count, booths_total_count = self._get_booth_stat_count('event.booth')
        for event in self:
            event.event_booth_count_available = booths_available_count.get(event.id, 0)
            event.event_booth_count = booths_total_count.get(event.id, 0)

    @api.depends('event_booth_slot_ids', 'event_booth_slot_ids.state')
    def _compute_event_booth_slots_count(self):
        booths_slot_available_count, booths_slot_total_count = self._get_booth_stat_count('event.booth.slot')
        for event in self:
            event.event_booth_slot_count_available = booths_slot_available_count.get(event.id, 0)
            event.event_booth_slot_count = booths_slot_total_count.get(event.id, 0)
