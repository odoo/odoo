# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TrackStage(models.Model):
    _inherit = 'event.track.stage'

    is_accepted = fields.Boolean(string='Accepted Stage')
