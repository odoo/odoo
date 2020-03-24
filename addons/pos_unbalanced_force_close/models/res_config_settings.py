# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_force_close_unbalanced = fields.Boolean("Force Close Unbalanced Session", implied_group='pos_unbalanced_force_close.group_force_close_unbalanced')
