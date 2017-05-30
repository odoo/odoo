# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrHolidaysInfo(models.TransientModel):
    _name = 'hr.holidays.info'

    @api.multi
    def action_approve(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            self.env['hr.holidays'].browse(active_ids).action_approve()

    @api.multi
    def action_refuse(self):
        active_ids = self.env.context.get('active_ids')
        if active_ids:
            self.env['hr.holidays'].browse(active_ids).action_refuse()
