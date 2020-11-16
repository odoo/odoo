# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class Event(models.Model):
    _inherit = 'event.event'

    # sponsors
    sponsor_ids = fields.One2many('event.sponsor', 'event_id', 'Sponsors')
    sponsor_count = fields.Integer('Sponsor Count', compute='_compute_sponsor_count')

    def _compute_sponsor_count(self):
        data = self.env['event.sponsor'].read_group([], ['event_id'], ['event_id'])
        result = dict((data['event_id'][0], data['event_id_count']) for data in data)
        for event in self:
            event.sponsor_count = result.get(event.id, 0)
