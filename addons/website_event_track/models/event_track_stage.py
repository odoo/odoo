# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models


class TrackStage(models.Model):
    _name = 'event.track.stage'
    _description = 'Event Track Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    description = fields.Text(string='Description', translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    mail_template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain=[('model', '=', 'event.track')],
        help="If set an email will be sent to the customer when the track reaches this step.")
    visibility = fields.Selection([
        ('public', 'Public'),
        ('private', 'Private'),
        ('unlisted', 'Unlisted')
    ], string='Visibility', required=True, default='private',
        help="Impacts the visibility of your tracks on the frontend.\n"\
            "- Public: The tracks will be visible for all users.\n"\
            "- Private: The tracks will be visible for the administrators only.\n"\
            "- Unlisted: The tracks will not be visible for all users."
    )
    is_accessible = fields.Boolean(string='Accessiblity',
        help="If checked, the access link of the tracks will be provided")
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    is_cancel = fields.Boolean(string='Canceled Stage')
    color = fields.Integer(string='Color')
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda s: _('Blocked'), translate=True, required=True,
        help='Override the default value displayed for the blocked state for kanban selection.')
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda s: _('Ready for Next Stage'), translate=True, required=True,
        help='Override the default value displayed for the done state for kanban selection.')
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda s: _('In Progress'), translate=True, required=True,
        help='Override the default value displayed for the normal state for kanban selection.')
