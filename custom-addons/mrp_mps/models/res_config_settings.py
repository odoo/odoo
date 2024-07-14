# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manufacturing_period = fields.Selection(related="company_id.manufacturing_period", string="Manufacturing Period", readonly=False)
    manufacturing_period_to_display = fields.Integer(
        related='company_id.manufacturing_period_to_display',
        string='Number of Manufacturing Period Columns', readonly=False)
