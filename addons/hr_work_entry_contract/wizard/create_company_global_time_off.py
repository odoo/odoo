# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayrollIndex(models.TransientModel):
    _name = 'create.company.global.time.off'
    _description = 'Create Company Public Time Off'

    name = fields.Char('Reason', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    date_from = fields.Datetime('Start Date', required=True)
    date_to = fields.Datetime('End Date', required=True)
    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type', required=True)

    def action_confirm(self):
        self.ensure_one()
        self.env['resource.calendar'].search([('company_id', '=', self.company_id.id)]).write({
            'leave_ids': [(0, 0, {
                'name': self.name,
                'date_from': self.date_from,
                'date_to': self.date_to,
                'time_type': 'leave',
                'work_entry_type_id': self.work_entry_type_id.id,
            })]
        })
