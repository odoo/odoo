# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = ['hr.employee', 'phone.validation.mixin']

    @api.onchange('work_phone', 'country_id')
    def _onchange_work_phone_validation(self):
        if self.work_phone:
            self.work_phone = self.phone_format(self.work_phone)

    @api.onchange('mobile_phone', 'country_id')
    def _onchange_mobile_phone_validation(self):
        if self.mobile_phone:
            self.mobile_phone = self.phone_format(self.mobile_phone)
