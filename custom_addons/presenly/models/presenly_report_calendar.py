from odoo import api, fields, models

class HrLeaveReportCalendarPresenly(models.Model):
    _inherit = 'hr.leave.report.calendar'

    presenly_approval_state = fields.Selection(
        related='leave_id.presenly_approval_state', string='Presenly Approval',
        related_sudo=True, readonly=True,
    )
    presenly_approval_progress = fields.Char(
        related='leave_id.presenly_approval_progress',
        related_sudo=True, readonly=True,
    )
    presenly_can_approve = fields.Boolean(
        compute='_compute_presenly_calendar_permissions',
    )
    presenly_can_reject = fields.Boolean(
        compute='_compute_presenly_calendar_permissions',
    )

    @api.depends_context('uid')
    @api.depends('leave_id.presenly_approval_state')
    def _compute_presenly_calendar_permissions(self):
        user = self.env.user
        for record in self:
            # leave_id is a native group-restricted field on this SQL view;
            # read it with sudo for the Presenly approval controls only.
            leave = record.sudo().leave_id
            record.presenly_can_approve = bool(
                leave
                and leave.presenly_approval_state == 'pending'
                and user in leave.presenly_current_approver_ids
            )
            record.presenly_can_reject = record.presenly_can_approve

    def action_presenly_approve(self):
        self.ensure_one()
        leave_id = self.sudo().leave_id.id
        self.env['hr.leave'].browse(leave_id).action_presenly_approve()
        return {'type': 'ir.actions.act_window_close'}

    def action_presenly_open_reject_wizard(self):
        self.ensure_one()
        leave_id = self.sudo().leave_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Time Off Request',
            'res_model': 'presenly.leave.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_leave_id': leave_id},
        }