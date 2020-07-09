# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_accrual = fields.Boolean(string="Accrual", config_parameter='hr_holidays.allow_accrual')
