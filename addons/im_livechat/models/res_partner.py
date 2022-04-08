# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class Partners(models.Model):
    """Update of res.partner class to take into account the livechat username."""
    _inherit = 'res.partner'

    user_livechat_username = fields.Char(compute='_compute_user_livechat_username')

    @api.depends('user_ids.livechat_username')
    def _compute_user_livechat_username(self):
        for partner in self:
            partner.user_livechat_username = next(iter(partner.user_ids.mapped('livechat_username')), False)
