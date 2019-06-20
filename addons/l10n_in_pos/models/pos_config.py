# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    l10n_in_unit_id = fields.Many2one(
        'res.partner',
        string="Operating Unit",
        ondelete="restrict",
        default=lambda self: self.env.user._get_default_unit())
