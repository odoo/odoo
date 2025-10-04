# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrHolidaysCancelLeave(models.TransientModel):
    _name = 'hr.holidays.refuse.leave.warning'
    _description = 'Refuse Leave Warning Wizard'

    leave_id = fields.Many2one('hr.leave', string="Time Off Request", required=True)

    def action_refuse_leave(self):
        self.ensure_one()
        self.leave_id.action_refuse()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._("Your time off has been Refused."),
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
