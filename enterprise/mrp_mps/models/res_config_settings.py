# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    manufacturing_period = fields.Selection(related="company_id.manufacturing_period", string="Manufacturing Period", readonly=False)
    manufacturing_period_to_display_year = fields.Integer(
        related='company_id.manufacturing_period_to_display_year',
        string='Number of Yearly Manufacturing Period Columns', readonly=False)
    manufacturing_period_to_display_month = fields.Integer(
        related='company_id.manufacturing_period_to_display_month',
        string='Number of Monthly Manufacturing Period Columns', readonly=False)
    manufacturing_period_to_display_week = fields.Integer(
        related='company_id.manufacturing_period_to_display_week',
        string='Number of Weekly Manufacturing Period Columns', readonly=False)
    manufacturing_period_to_display_day = fields.Integer(
        related='company_id.manufacturing_period_to_display_day',
        string='Number of Daily Manufacturing Period Columns', readonly=False)
