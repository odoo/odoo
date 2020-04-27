# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def _default_accrual(self):
        if self.env['ir.module.module'].search([('name', '=', 'hr_work_entry_holidays'), ('state', '=', 'installed')]) \
                and self.user_has_groups('hr_holidays.group_allow_accrual'):
            return True
        return False

    enable_accrual = fields.Boolean("Accrual", default=_default_accrual)
    module_hr_work_entry_holidays = fields.Boolean()
    group_allow_accrual = fields.Boolean(implied_group='hr_holidays.group_allow_accrual')

    def set_values(self):
        if self.enable_accrual:
            self.module_hr_work_entry_holidays = True
            self.group_allow_accrual = True
        super(ResConfigSettings, self).set_values()

