# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TrackLocation(models.Model):
    _name = "event.track.location"
    _description = 'Event Track Location'

    name = fields.Char('Location', required=True)
