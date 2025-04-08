# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    role_color = fields.Integer(string='Role Color', compute='_compute_role_color', store=False)

    def _compute_role_color(self):
        for slot in self:
            slot.role_color = (
                slot.role_ids[0].color
                if slot.role_ids else 0)

    im_status = fields.Char(related='user_id.im_status')
