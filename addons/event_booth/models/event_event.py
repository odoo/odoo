# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models
from odoo import Command


class EventEvent(models.Model):
    _inherit = 'event.event'

    event_booth_ids = fields.One2many(
        'event.booth', 'event_id', string='Booths', copy=True,
        compute='_compute_event_booth_ids', readonly=False, store=True)
    event_booth_count = fields.Integer(
        string='Total Booths',
        compute='_compute_event_booth_count')
    event_booth_count_available = fields.Integer(
        string='Available Booths',
        compute='_compute_event_booth_count')
    event_booth_category_ids = fields.Many2many(
        'event.booth.category', compute='_compute_event_booth_category_ids')
    event_booth_category_available_ids = fields.Many2many(
        'event.booth.category', compute='_compute_event_booth_category_available_ids',
        help='Booth Category for which booths are still available. Used in frontend')

    @api.depends('event_type_id')
    def _compute_event_booth_ids(self):
        """ Update event configuration from its event type. Depends are set only
        on event_type_id itself, not its sub fields. Purpose is to emulate an
        onchange: if event type is changed, update event configuration. Changing
        event type content itself should not trigger this method.

        When synchronizing booths:

          * lines that are available are removed;
          * template lines are added;
        """
        for event in self:
            if not event.event_type_id and not event.event_booth_ids:
                event.event_booth_ids = False
                continue

            # booths to keep: those that are not available
            booths_to_remove = event.event_booth_ids.filtered(lambda booth: booth.is_available)
            command = [Command.unlink(booth.id) for booth in booths_to_remove]
            if event.event_type_id.event_type_booth_ids:
                command += [
                    Command.create({
                        attribute_name: line[attribute_name] if not isinstance(line[attribute_name], models.BaseModel) else line[attribute_name].id
                        for attribute_name in self.env['event.type.booth']._get_event_booth_fields_whitelist()
                    }) for line in event.event_type_id.event_type_booth_ids
                ]
            event.event_booth_ids = command

    def _get_booth_stat_count(self):
        elements = self.env['event.booth'].sudo()._read_group(
            [('event_id', 'in', self.ids)],
            ['event_id', 'state'], ['__count']
        )
        elements_total_count = defaultdict(int)
        elements_available_count = dict()
        for event, state, count in elements:
            if state == 'available':
                elements_available_count[event.id] = count
            elements_total_count[event.id] += count
        return elements_available_count, elements_total_count

    @api.depends('event_booth_ids', 'event_booth_ids.state')
    def _compute_event_booth_count(self):
        if self.ids and all(bool(event.id) for event in self):  # no new/onchange mode -> optimized
            booths_available_count, booths_total_count = self._get_booth_stat_count()
            for event in self:
                event.event_booth_count_available = booths_available_count.get(event.id, 0)
                event.event_booth_count = booths_total_count.get(event.id, 0)
        else:
            for event in self:
                event.event_booth_count = len(event.event_booth_ids)
                event.event_booth_count_available = len(event.event_booth_ids.filtered(lambda booth: booth.is_available))

    @api.depends('event_booth_ids.booth_category_id')
    def _compute_event_booth_category_ids(self):
        for event in self:
            event.event_booth_category_ids = event.event_booth_ids.booth_category_id

    @api.depends('event_booth_ids.is_available')
    def _compute_event_booth_category_available_ids(self):
        for event in self:
            event.event_booth_category_available_ids = event.event_booth_ids.filtered(lambda booth: booth.is_available).booth_category_id
