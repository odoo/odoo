# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from random import randint

from odoo import api, fields, models


class ResourceResource(models.Model):
    _inherit = 'resource.resource'

    role_color = fields.Integer(string='Role Color', compute='_compute_role_color', store=False)
    im_status = fields.Char(related='user_id.im_status')

    def get_avatar_card_data(self, fields):
        return self.env['resource.resource'].search_read(
            domain=[('id', 'in', self.ids)],
        )

    @api.depends("role_ids")
    def _compute_role_color(self):
        for slot in self:
            if slot.role_ids:
                slot.role_color = slot.role_ids[0].color
            else:
                # fallback to prevent not having color in dark mode (dont use 0)
                slot.role_color = 1
