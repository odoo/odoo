# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class GamificationChallenge(models.Model):
    _inherit = 'gamification.challenge'

    challenge_category = fields.Selection(selection_add=[
        ('forum', 'Website / Forum')
    ], ondelete={'forum': 'set default'})
