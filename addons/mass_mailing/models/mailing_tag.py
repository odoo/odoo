# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random

from odoo import fields, models


class MassMailingTestingCampaignTag(models.Model):
    _name = 'mailing.ab.testing.tag'
    _description = 'Testing Mailing Tag'

    def _default_color(self):
        return random.randint(1, 11)

    name = fields.Char('Name')
    color = fields.Integer('Color Index', default=lambda self: self._default_color())
