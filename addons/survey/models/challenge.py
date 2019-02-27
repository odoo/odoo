# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Challenge(models.Model):
    _inherit = 'gamification.challenge'

    category = fields.Selection(selection_add=[('certification', 'Certifications')])
