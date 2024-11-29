# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTrackStage(models.Model):
    _name = 'event.track.stage'
    _description = 'Event Track Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    mail_template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain=[('model', '=', 'event.track')],
        help="If set an email will be sent to the customer when the track reaches this step.")
    # legends
    color = fields.Integer(string='Color')
    description = fields.Text(string='Description', translate=True)
    legend_blocked = fields.Char('Red Kanban Label', default=lambda s: s.env._('Blocked'), translate=True)
    legend_done = fields.Char('Green Kanban Label', default=lambda s: s.env._('Ready for Next Stage'), translate=True)
    legend_normal = fields.Char('Grey Kanban Label', default=lambda s: s.env._('In Progress'), translate=True)
    # pipe
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    is_visible_in_agenda = fields.Boolean(
        string='Visible in agenda', compute='_compute_is_visible_in_agenda', store=True,
        help='If checked, the related tracks will be visible in the frontend.')
    is_fully_accessible = fields.Boolean(
        string='Fully accessible', compute='_compute_is_fully_accessible', store=True,
        help='If checked, automatically publish tracks so that access links to customers are provided.')
    is_cancel = fields.Boolean(string='Cancelled Stage')

    @api.depends('is_cancel', 'is_fully_accessible')
    def _compute_is_visible_in_agenda(self):
        for record in self:
            if record.is_cancel:
                record.is_visible_in_agenda = False
            elif record.is_fully_accessible:
                record.is_visible_in_agenda = True

    @api.depends('is_cancel', 'is_visible_in_agenda')
    def _compute_is_fully_accessible(self):
        for record in self:
            if record.is_cancel or not record.is_visible_in_agenda:
                record.is_fully_accessible = False
