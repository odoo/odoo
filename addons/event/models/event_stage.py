# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class EventStage(models.Model):
    _name = 'event.stage'
    _description = 'Event Stage'
    _order = 'sequence, name'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(string='Stage description', translate=True)
    sequence = fields.Integer('Sequence', default=1)
    fold = fields.Boolean(string='Folded in Kanban', default=False)
    pipe_end = fields.Boolean(
        string='End Stage', default=False,
        help='Events will automatically be moved into this stage when they are finished. The event moved into this stage will automatically be set as green.')
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: s.env._('Blocked'), translate=True, prefetch='legend', required=True,
        help='Override the default value displayed for the blocked state for kanban selection.')
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: s.env._('Ready for Next Stage'), translate=True, prefetch='legend', required=True,
        help='Override the default value displayed for the done state for kanban selection.')
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: s.env._('In Progress'), translate=True, prefetch='legend', required=True,
        help='Override the default value displayed for the normal state for kanban selection.')
