# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrTimesheetCurrentOpen(models.TransientModel):
    _name = 'hr.timesheet.current.open'
    _description = 'hr.timesheet.current.open'

    @api.model
    def open_timesheet(self):
        view_type = 'form,tree'

        hr_timesheets_ids = self.env['hr_timesheet_sheet.sheet'].search([('user_id', '=', self.env.uid),
                                                                         ('state', 'in', ('draft', 'new')),
                                                                         ('date_from', '<=', fields.Date.today()),
                                                                         ('date_to', '>=', fields.Date.today())])
        if len(hr_timesheets_ids) > 1:
            view_type = 'tree,form'
            domain = "[('id','in',["+','.join(map(str, hr_timesheets_ids))+"]),('user_id', '=', uid)]"
        else:
            domain = "[('user_id', '=', uid)]"
        value = {
            'domain': domain,
            'name': _('Open Timesheet'),
            'view_type': 'form',
            'view_mode': view_type,
            'res_model': 'hr_timesheet_sheet.sheet',
            'view_id': False,
            'type': 'ir.actions.act_window'
        }
        if len(hr_timesheets_ids) == 1:
            value['res_id'] = hr_timesheets_ids.ids[0]
        return value
