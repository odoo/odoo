# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    def set_values(self):
        super().set_values()
        if not self.hr_attendance_display_overtime:
            self.env['hr.leave.type'].search([('requires_allocation', '=', 'extra_hours')]).write({'active': False})
