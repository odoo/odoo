# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventTrackStage(models.Model):
    _name = 'event.track.stage'
    _description = 'Event Track Stage'
    _order = 'sequence, id'

    def _get_default_event_ids(self):
        default_event_id = self.env.context.get('default_event_id')
        return [default_event_id] if default_event_id else None

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    event_ids = fields.Many2many(
        'event.event', 'event_track_stage_event_rel', 'stage_id', 'event_id',
        string='Events', default=lambda self: self._get_default_event_ids(),
        help="Events in which this stage is available for tracks. A stage can be shared "
             "among several events following the same workflow.")
    event_type_ids = fields.Many2many(
        'event.type', 'event_track_stage_event_type_rel', 'stage_id', 'event_type_id',
        string='Event Templates',
        help="Events created from these templates get this stage by default.")
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

    @api.constrains('event_ids')
    def _check_event_ids(self):
        """ Writing this side of the relation does not trigger the constraint
        on event.event: check the events having tracks in these stages. """
        events = self.env['event.track'].with_context(active_test=False).search(
            [('stage_id', 'in', self.ids)]).event_id
        events._check_track_stage_ids()
