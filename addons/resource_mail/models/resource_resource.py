# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    def _default_color(self):
        return randint(1, 11)

    color = fields.Integer(default=_default_color)
    im_status = fields.Char(related='user_id.im_status')

    def get_avatar_card_data(self, fields):
        return self.read(fields)
