# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_allow_accrual = fields.Boolean("Accrual",
                                                implied_group='hr_holidays.group_allow_accrual')

