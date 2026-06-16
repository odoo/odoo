from odoo import api, fields, models, _
from odoo.exceptions import UserError

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def _is_annual_leave_logic(self):
        """Check if the leave is an annual vacation handled by KSW_annual_leave."""
        return self.holiday_status_id and self.holiday_status_id.is_annual_leave

    def action_approve(self, check_state=True):
        """Enforce Direct Manager approval for non-annual leaves."""
        for leave in self:
            if not leave._is_annual_leave_logic() and leave.state == 'confirm':
                # Direct manager is leave_manager_id or parent_id.user_id
                manager_user = leave.employee_id.leave_manager_id or leave.employee_id.parent_id.user_id
                
                if not self.env.su:
                    if not manager_user:
                        raise UserError(_("No direct manager user found for %s. Please assign a manager with a linked user to this employee.") % leave.employee_id.name)
                    
                    if self.env.user != manager_user:
                        raise UserError(_("Only the direct manager (%s) can approve this step.") % manager_user.name)

        return super().action_approve(check_state=check_state)

    def action_validate(self):
        """Enforce configured HR Manager approval for non-annual leaves."""
        for leave in self:
            if not leave._is_annual_leave_logic():
                hr_manager = leave.company_id.x_hr_leave_manager_id
                
                if leave.state == 'validate1':
                    if not self.env.su:
                        if not hr_manager:
                            raise UserError(_("HR Leave Manager is not configured in settings."))
                        if self.env.user != hr_manager:
                            raise UserError(_("Only the configured HR Manager (%s) can approve this step.") % hr_manager.name)

        return super().action_validate()

    def _action_approve_attendance_based(self, check_state=True):
        """Override KSW_attendance_leave to remove second-step bypass."""
        # We need to re-implement the logic but without the bypass
        attendance_leaves = self.filtered('x_attendance_ids')
        if not attendance_leaves:
            return super()._action_approve_attendance_based(check_state=check_state)

        for leave in attendance_leaves:
            if not leave._is_annual_leave_logic():
                if check_state and leave.state != 'confirm':
                    from odoo.exceptions import ValidationError
                    raise ValidationError(_('Time off request must be confirmed ("To Approve") in order to approve it.'))

                current_employee = self.env.user.employee_id
                leave_no_track = leave.with_context(tracking_disable=True)

                if leave.holiday_status_id.leave_validation_type == 'both':
                    # REMOVED: check for hr_holidays.group_hr_holidays_manager bypass
                    # Force movement to validate1 even if user is an HR manager,
                    # UNLESS the user is the configured HR Manager AND we want to allow 1-step for them?
                    # The requirement says "second approval can only be approved by the hr manager".
                    # If the DM is also the HR manager, they'd still have to click twice?
                    # Usually yes, but Odoo standard allows 1-step if the same person is both.
                    # But here the user said "robust so first approval can only be approved by the direct manager... and second... by the hr manager".
                    
                    hr_manager = leave.company_id.x_hr_leave_manager_id
                    if self.env.user == hr_manager and leave.employee_id.parent_id.user_id != hr_manager:
                        # If the HR manager is trying to approve a 1st step, should we allow it?
                        # User said "first approval can only be approved by the direct manager and no one can do anything else about it".
                        # So HR manager CANNOT approve the first step unless they are also the DM.
                        pass # action_approve already blocked this above if not DM

                    leave_no_track.write({
                        'state': 'validate1',
                        'first_approver_id': current_employee.id,
                    })
                else:
                    leave_no_track.write({
                        'state': 'validate',
                        'first_approver_id': current_employee.id,
                    })
                leave._validate_leave_request()
            else:
                # For annual leaves, keep original behavior (though they shouldn't hit this if they use annual_multi)
                super(HrLeave, leave)._action_approve_attendance_based(check_state=check_state)

    def _action_validate(self, check_state=True):
        """Override KSW_attendance_leave to ensure strict 2nd step for attendance leaves."""
        attendance_leaves = self.filtered('x_attendance_ids')
        if not attendance_leaves:
            return super()._action_validate(check_state=check_state)

        for leave in attendance_leaves:
            if not leave._is_annual_leave_logic():
                # Enforce HR Manager check for validate1 -> validate
                if leave.state == 'validate1':
                    hr_manager = leave.company_id.x_hr_leave_manager_id
                    if hr_manager and self.env.user != hr_manager and not self.env.su:
                        raise UserError(_("Only the configured HR Manager (%s) can approve this step.") % hr_manager.name)

                # Now replicate the write to 'validate' but correctly
                current_employee = self.env.user.employee_id
                att_no_track = leave.with_context(tracking_disable=True)
                
                if leave.state == 'validate1':
                    att_no_track.write({
                        'state': 'validate',
                        'second_approver_id': current_employee.id,
                    })
                else:
                    att_no_track.write({
                        'state': 'validate',
                        'first_approver_id': current_employee.id,
                    })
                
                leave._validate_leave_request()
                if not self.env.context.get('leave_fast_create'):
                    leave.filtered(lambda h: h.validation_type != 'no_validation').activity_update()
            else:
                super(HrLeave, leave)._action_validate(check_state=check_state)

    def _get_responsible_for_approval(self):
        """Direct activities to the configured HR Manager for the second step."""
        if not self._is_annual_leave_logic():
            if self.validation_type == 'both' and self.state == 'validate1':
                hr_manager = self.company_id.x_hr_leave_manager_id
                if hr_manager:
                    return hr_manager
        return super()._get_responsible_for_approval()
