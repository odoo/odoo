# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class QuizQuestion(models.Model):
    _inherit = "quiz.question"

    track_id = fields.Many2one('event.track', string="Event Track")
