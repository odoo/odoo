# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TrackVisitor(models.Model):
    _name = 'event.track.visitor'
    _inherit = ['event.track.visitor', 'quiz.partner.mixin']
