# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTypeBoothCategory(models.Model):
    _name = 'event.type.booth.category'
    _description = 'Event Type Booth Category'
    _inherit = ['image.mixin']

    name = fields.Char(string='Name', required=True)
    event_type_id = fields.Many2one(
        'event.type', string='Event Category', ondelete='cascade', required=True)
    is_multi_slots = fields.Boolean(
        string='Multi Slots',
        help='This option enables the creation of multiple slots that will be available for the booth')
    description = fields.Html(string='Description')

    @api.model
    def _get_event_booth_category_fields_whitelist(self):
        return ['name', 'image_1920', 'is_multi_slots', 'description']


class EventBoothCategory(models.Model):
    _name = 'event.booth.category'
    _inherit = 'event.type.booth.category'
    _description = 'Event Booth Category'

    event_type_id = fields.Many2one(ondelete='set null', required=False)
    event_id = fields.Many2one(
        'event.event', string='Event', ondelete='cascade', required=True)
    event_booth_ids = fields.One2many('event.booth', 'booth_category_id', string='Booths')
    event_booth_count = fields.Integer(string='Total Booths', compute='_compute_event_booth_count')
    event_booth_count_available = fields.Integer(string='Available Booths', compute='_compute_event_booth_count')

    _sql_constraints = [
        ('name_uniq', 'unique (name, event_id)', "Category name already exists for this event !"),
    ]

    @api.depends('event_booth_ids')
    def _compute_event_booth_count(self):
        booths = self.env['event.booth'].read_group(
            [('booth_category_id', 'in', self.ids)],
            ['booth_category_id', 'state'], ['booth_category_id', 'state'], lazy=False)
        booths_total_count = dict()
        booths_available_count = dict()
        for booth in booths:
            booth_category_id = booth['booth_category_id'][0]
            if booth['state'] == 'available':
                booths_available_count[booth_category_id] = booth['__count']
            booths_total_count.setdefault(booth_category_id, 0)
            booths_total_count[booth_category_id] += booth['__count']

        for category in self:
            category.event_booth_count = booths_total_count.get(category.id, 0)
            category.event_booth_count_available = booths_available_count.get(category.id, 0)
