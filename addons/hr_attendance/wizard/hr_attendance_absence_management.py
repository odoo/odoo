# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrAttendanceAbsenceManagement(models.TransientModel):
    _name = 'hr.attendance.absence.management.wizard'
    _description = 'Recommendation when fall-behind rule is saved without Absence Management'

    ruleset_id = fields.Many2one('hr.attendance.overtime.ruleset', string='Ruleset')
    rule_id = fields.Many2one('hr.attendance.overtime.rule', string='Rule')

    def action_confirm_and_activate(self):
        settings = self.env['res.config.settings'].create({
            'company_id': self.env.company.id,
            'absence_management': True,
        }).execute()

        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_without_activate(self):
        return {'type': 'ir.actions.act_window_close'}

    def action_discard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.attendance.overtime.rule',
            'view_mode': 'form',
            'res_id': self.rule_id.id,
            'target': 'current',
        }
