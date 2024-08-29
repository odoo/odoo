# -*- coding: utf-8 -*-
from odoo.addons import gamification
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class GamificationChallenge(models.Model, gamification.GamificationChallenge):

    challenge_category = fields.Selection(selection_add=[
        ('certification', 'Certifications')
    ], ondelete={'certification': 'set default'})
