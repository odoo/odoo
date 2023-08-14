# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TrackStage(models.Model):
    _name = 'event.track.stage'
    _description = 'Event Track Stage'
    _order = 'sequence, id'

    name = fields.Char(string='Stage Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=1)
    mail_template_id = fields.Many2one(
        'mail.template', string='Email Template',
        domain=[('model', '=', 'event.track')],
        help="If set an email will be sent to the customer when the track reaches this step.")
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view when there are no records in that stage to display.')
    is_accepted = fields.Boolean(
        string='Accepted Stage',
        help='Accepted tracks are displayed in agenda views but not accessible.')
    is_done = fields.Boolean(
        string='Done Stage',
        help='Done tracks are automatically published so that they are available in frontend.')
    is_cancel = fields.Boolean(string='Canceled Stage')
    is_done = fields.Boolean()
    color = fields.Integer(string='Color')
