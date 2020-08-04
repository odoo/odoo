# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TrackStage(models.Model):
    _inherit = 'event.track.stage'

    is_accepted = fields.Boolean(
        string='Accepted Stage',
        help='Accepted tracks are displayed in agenda views but not accessible.')
    is_done = fields.Boolean(help='Done tracks are automatically published so that they are available in frontend.')