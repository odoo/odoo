# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bacs_sun = fields.Char(related='company_id.bacs_sun', string='Service User Number', readonly=False,
        help="Service user number of your company within BACS. Write 'HSBC' here if your bank does not provide one.")
