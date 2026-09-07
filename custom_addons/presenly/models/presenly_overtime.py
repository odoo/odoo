from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PresenlyOvertimeRequest(models.Model):
    _name = 'presenly.overtime.request'
    _description = 'Presenly Overtime / Lembur Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'presenly.deletion.log.mixin']
    _order = 'create_date desc'

    def _default_employee(self):
        return self.env.user.employee_id

    name = fields.Char(default='New', readonly=True, copy=False, index=True)
    employee_id = fields.Many2one(
        'hr.employee', index=True, default=_default_employee, tracking=True,
    )
    company_id = fields.Many2one(
        related='employee_id.company_id', store=True, index=True,
    )
    work_location_id = fields.Many2one(
        'hr.work.location', index=True, tracking=True, check_company=True,
    )
    date = fields.Date(
        string='Overtime Day', required=True, tracking=True, index=True,
    )
    hour_from = fields.Float(
        string='Start Hour (24H)', required=True, tracking=True, default=18.0,
    )
    hour_to = fields.Float(
        string='End Hour (24H)', required=True, tracking=True, default=21.0,
    )
    duration_hours = fields.Float(
        compute='_compute_duration_hours', string='Duration (hours)',
        readonly=True, store=True,
    )
    reason = fields.Text(tracking=True)
    has_attendance_evidence = fields.Boolean(
        compute='_compute_has_attendance_evidence', string='Has Attendance Evidence',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, required=True)
    rejection_reason = fields.Text(readonly=True)
    approval_level = fields.Integer(default=0, readonly=True)
    presenly_approval_request_id = fields.Many2one(
        'presenly.approval.request', string='Approval Journey',
        readonly=True, copy=False, ondelete='restrict',
    )
    presenly_approval_step_ids = fields.One2many(
        'presenly.approval.step', compute='_compute_presenly_approval_steps',
        string='Approval Steps',
    )
    presenly_pending_approver_ids = fields.Many2many(
        'res.users', 'presenly_overtime_pending_approver_rel',
        'overtime_id', 'user_id', string='Pending Approvers',
        readonly=True, copy=False,
    )
    presenly_approver_history_ids = fields.Many2many(
        'res.users', 'presenly_overtime_approver_history_rel',
        'overtime_id', 'user_id', string='Approver History',
        readonly=True, copy=False,
    )
    is_request_owner = fields.Boolean(compute='_compute_ui_permissions')
    can_submit = fields.Boolean(compute='_compute_ui_permissions')
    can_approve = fields.Boolean(compute='_compute_ui_permissions')
    can_reject = fields.Boolean(compute='_compute_ui_permissions')
    can_cancel = fields.Boolean(compute='_compute_ui_permissions')
    can_change_employee = fields.Boolean(
        compute='_compute_can_change_employee',
        string='Can Edit Employee',
    )

    presenly_can_approve_api = fields.Boolean(
        compute='_compute_presenly_api_flags', string='Can Approve (API)',
    )
    presenly_can_reject_api = fields.Boolean(
        compute='_compute_presenly_api_flags', string='Can Reject (API)',
    )
    presenly_can_cancel_api = fields.Boolean(
        compute='_compute_presenly_api_flags', string='Can Cancel (API)',
    )

    _valid_hours = models.Constraint(
        'CHECK(hour_from >= 0 AND hour_from < hour_to AND hour_to <= 24)',
        'Hours must be valid 24h values: 0 <= start < end <= 24.',
    )

    @api.depends('hour_from', 'hour_to')
    def _compute_duration_hours(self):
        for overtime in self:
            if overtime.hour_from is not None and overtime.hour_to is not None:
                overtime.duration_hours = round(
                    overtime.hour_to - overtime.hour_from, 4,
                )
            else:
                overtime.duration_hours = 0.0

    @api.depends('employee_id', 'date')
    def _compute_has_attendance_evidence(self):
        attendance_model = self.env['hr.attendance'].sudo()
        for overtime in self:
            if not overtime.employee_id or not overtime.date:
                overtime.has_attendance_evidence = False
                continue
            overtime.has_attendance_evidence = bool(
                attendance_model.search_count([
                    ('employee_id', '=', overtime.employee_id.id),
                    ('date', '=', overtime.date),
                ], limit=1)
            )

    @api.depends('presenly_approval_request_id.step_ids')
    def _compute_presenly_approval_steps(self):
        for overtime in self:
            overtime.presenly_approval_step_ids = (
                overtime.presenly_approval_request_id.step_ids
            )

    @api.depends_context('uid')
    def _compute_can_change_employee(self):
        """Only HR / Administrator may pick another employee.

        A plain employee has no HR access and can only submit for their own
        user-linked employee record; grant one of the Presenly HR/Administrator
        roles to allow choosing other employees.
        """
        user = self.env.user
        allowed = (
            user.has_group('presenly.group_presenly_hr')
            or user.has_group('presenly.group_presenly_manager')
        )
        for overtime in self:
            overtime.can_change_employee = allowed

    @api.depends_context('uid')
    @api.depends('employee_id', 'state')
    def _compute_ui_permissions(self):
        user = self.env.user
        is_manager = user.has_group('presenly.group_presenly_manager')
        is_hr = user.has_group('presenly.group_presenly_hr')
        for overtime in self:
            owner = overtime.employee_id.user_id == user
            pending_approvers = overtime.presenly_approval_request_id.current_approver_ids \
                if overtime.presenly_approval_request_id \
                else overtime.presenly_pending_approver_ids
            overtime.is_request_owner = owner
            overtime.can_submit = bool(
                overtime.id
                and overtime.state == 'draft'
                and (owner or is_manager)
            )
            overtime.can_approve = bool(
                overtime.state == 'submitted'
                and user in pending_approvers
            )
            overtime.can_reject = overtime.can_approve
            overtime.can_cancel = bool(
                overtime.id
                and overtime.state in ('draft', 'submitted')
                and (owner or is_manager or is_hr)
            )

    @api.depends_context('uid')
    @api.depends('can_approve', 'can_reject', 'can_cancel')
    def _compute_presenly_api_flags(self):
        for overtime in self:
            overtime.presenly_can_approve_api = overtime.can_approve
            overtime.presenly_can_reject_api = overtime.can_reject
            overtime.presenly_can_cancel_api = overtime.can_cancel

    @api.model_create_multi
    def create(self, values_list):
        user = self.env.user
        is_hr = (
            user.has_group('presenly.group_presenly_hr')
            or user.has_group('presenly.group_presenly_manager')
        )
        for values in values_list:
            if values.get('name', 'New') == 'New':
                values['name'] = self.env['ir.sequence'].next_by_code(
                    'presenly.overtime'
                ) or 'New'
            if not is_hr:
                own = user.employee_id
                if not own:
                    raise ValidationError(
                        'You have no active Employee record on this user.'
                    )
                values['employee_id'] = own.id
            if not self.env.context.get('presenly_workflow'):
                values['state'] = 'draft'
                values['approval_level'] = 0
                values['rejection_reason'] = False
                values['presenly_pending_approver_ids'] = [(5, 0, 0)]
                values['presenly_approver_history_ids'] = [(5, 0, 0)]
                values['presenly_approval_request_id'] = False
        return super().create(values_list)

    def write(self, values):
        if self.env.context.get('presenly_workflow'):
            return super().write(values)
        workflow_fields = {
            'state', 'approval_level', 'rejection_reason',
            'presenly_pending_approver_ids', 'presenly_approver_history_ids',
            'presenly_approval_request_id',
        }
        if workflow_fields.intersection(values):
            raise UserError(
                'Request status can only be changed using Presenly workflow actions.'
            )
        if not self.env.su and not (
            self.env.user.has_group('presenly.group_presenly_hr')
            or self.env.user.has_group('presenly.group_presenly_manager')
        ):
            own = self.env.user.employee_id
            if 'employee_id' in values and own and values['employee_id'] != own.id:
                raise UserError(
                    'You can only submit overtime for yourself. Ask HR to '
                    'assign additional access if you need to submit for others.'
                )
        transaction_fields = {
            'employee_id', 'work_location_id', 'date', 'hour_from', 'hour_to',
            'reason',
        }
        if transaction_fields.intersection(values) and any(
            record.state != 'draft' for record in self
        ):
            raise UserError('Only draft overtime requests can be edited.')
        return super().write(values)

    def _presenly_workflow_write(self, values):
        return self.with_context(presenly_workflow=True).write(values)

    def _presenly_rules(self):
        return self.env['presenly.approval.rule']._get_rules(self, 'overtime')

    def _presenly_pending_approver_users(self):
        self.ensure_one()
        if self.presenly_approval_request_id:
            return self.presenly_approval_request_id.current_approver_ids
        return self.presenly_pending_approver_ids

    def _presenly_check_approver(self):
        self.ensure_one()
        if self.state != 'submitted' or not self.presenly_approval_request_id:
            raise UserError('Only submitted overtime requests can be approved.')
        self.presenly_approval_request_id._check_current_approver()
        return self.presenly_approval_request_id.current_step_id

    def _presenly_close_approval_activities(self, users):
        activity_type = self.env.ref(
            'mail.mail_activity_data_todo', raise_if_not_found=False,
        )
        if activity_type and users:
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('user_id', 'in', users.ids),
            ]).unlink()

    def _presenly_notify_current_approvers(self):
        activity_type_xmlid = 'mail.mail_activity_data_todo'
        if not self.env.ref(activity_type_xmlid, raise_if_not_found=False):
            return
        for overtime in self:
            approval = overtime.presenly_approval_request_id
            if approval.state != 'pending' or not approval.current_step_id:
                continue
            for user in approval.current_approver_ids:
                overtime.activity_schedule(
                    activity_type_xmlid,
                    user_id=user.id,
                    note=(
                        f'Overtime approval {approval.progress_display}: '
                        f'{overtime.display_name}'
                    ),
                )

    @api.constrains('employee_id', 'date', 'state')
    def _check_one_per_day(self):
        for overtime in self:
            if not overtime.employee_id or not overtime.date:
                continue
            if overtime.state in ('cancelled',):
                continue
            duplicate = self.search([
                ('id', '!=', overtime.id),
                ('employee_id', '=', overtime.employee_id.id),
                ('date', '=', overtime.date),
                ('state', 'in', ('draft', 'submitted', 'approved')),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    'An overtime request already exists for this employee '
                    'on %s.' % overtime.date
                )

    def _presenly_validate_submission(self):
        for overtime in self:
            if not overtime.employee_id:
                raise ValidationError('Employee is required.')
            if not overtime.work_location_id:
                raise ValidationError('Work Location is required.')
            if overtime.hour_from is None or overtime.hour_to is None:
                raise ValidationError('Start and end hour are required.')
            if not (
                0 <= overtime.hour_from < overtime.hour_to <= 24
            ):
                raise ValidationError(
                    'Hours must be valid 24h values: 0 <= start < end <= 24.'
                )
            if (overtime.reason or '').strip():
                pass
            if not overtime.has_attendance_evidence:
                raise ValidationError(
                    'No Attendance record exists for this employee as evidence. '
                    'Overtime can only be claimed on days with attendance data.'
                )
            if not overtime._presenly_rules():
                raise ValidationError(
                    'No complete Presenly Approval Route is configured for overtime.'
                )

    def action_submit(self):
        for overtime in self:
            if not overtime.can_submit or overtime.state != 'draft':
                raise UserError('Only an authorized draft request can be submitted.')
            overtime._presenly_validate_submission()
            rules = overtime._presenly_rules()
            approval = self.env[
                'presenly.approval.request'
            ]._create_for_target(overtime, rules)
            approvers = approval.current_approver_ids
            overtime._presenly_workflow_write({
                'state': 'submitted',
                'approval_level': 0,
                'rejection_reason': False,
                'presenly_approval_request_id': approval.id,
                'presenly_pending_approver_ids': [(6, 0, approvers.ids)],
                'presenly_approver_history_ids': [(6, 0, approvers.ids)],
            })
            overtime._presenly_notify_current_approvers()
        return True

    def action_presenly_approve(self):
        for overtime in self:
            current = overtime._presenly_check_approver()
            current_users = current.assigned_user_ids
            next_step, completed = overtime.presenly_approval_request_id._approve_current()
            self.env['presenly.approval.log'].sudo().create({
                'request_model': 'presenly.overtime.request',
                'request_res_id': overtime.id,
                'level': current.level,
                'approver_id': self.env.user.id,
                'decision': 'approved',
            })
            overtime._presenly_close_approval_activities(current_users)
            if completed:
                overtime._presenly_workflow_write({
                    'state': 'approved',
                    'approval_level': len(
                        overtime.presenly_approval_request_id.step_ids
                    ),
                    'presenly_pending_approver_ids': [(5, 0, 0)],
                })
            else:
                overtime._presenly_workflow_write({
                    'approval_level': next_step.level - 1,
                    'presenly_pending_approver_ids': [
                        (6, 0, next_step.assigned_user_ids.ids),
                    ],
                    'presenly_approver_history_ids': [
                        (4, user_id) for user_id in next_step.assigned_user_ids.ids
                    ],
                })
                overtime._presenly_notify_current_approvers()
        return True

    def action_approve(self):
        return self.action_presenly_approve()

    def action_presenly_open_reject_wizard(self):
        self.ensure_one()
        self._presenly_check_approver()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Overtime Request',
            'res_model': 'presenly.overtime.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_overtime_id': self.id},
        }

    def action_presenly_reject(self, reason):
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError('A rejection reason is required.')
        for overtime in self:
            current = overtime._presenly_check_approver()
            current_users = current.assigned_user_ids
            overtime.presenly_approval_request_id._reject_current(reason)
            self.env['presenly.approval.log'].sudo().create({
                'request_model': 'presenly.overtime.request',
                'request_res_id': overtime.id,
                'level': current.level,
                'approver_id': self.env.user.id,
                'decision': 'rejected',
                'note': reason,
            })
            overtime._presenly_close_approval_activities(current_users)
            overtime._presenly_workflow_write({
                'state': 'rejected',
                'rejection_reason': reason,
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
        return True

    def action_reject(self, reason):
        return self.action_presenly_reject(reason)

    def action_cancel(self):
        for overtime in self:
            if not overtime.can_cancel:
                raise UserError('You cannot cancel this overtime request.')
            if overtime.presenly_approval_request_id:
                overtime.presenly_approval_request_id._cancel_pending()
            overtime._presenly_close_approval_activities(
                overtime.presenly_pending_approver_ids
            )
            overtime._presenly_workflow_write({
                'state': 'cancelled',
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
        return True

    @api.model
    def action_open_presenly_approval_queue(self):
        candidates = self.search([
            ('state', '=', 'submitted'),
            ('company_id', 'in', self.env.companies.ids),
        ])
        pending = candidates.filtered(
            lambda item: self.env.user in item._presenly_pending_approver_users()
        )
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_overtime_approvals'
        )
        action['domain'] = [('id', 'in', pending.ids)]
        return action

    def unlink(self):
        is_admin = self.env.su or self.env.user.has_group(
            'presenly.group_presenly_manager'
        )
        if not is_admin:
            if not self.env.user.has_group('presenly.group_presenly_hr'):
                raise UserError(
                    'Only a Presenly Administrator or HR Officer can delete '
                    'overtime requests.'
                )
            not_hr_ok = self.filtered(
                lambda request: request.state not in
                ('draft', 'rejected', 'cancelled')
            )
            if not_hr_ok:
                raise UserError(
                    'HR can only delete draft, rejected, or cancelled '
                    'overtime requests.'
                )
        for overtime in self:
            overtime._presenly_purge_approval(keep_logs=True)
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', overtime._name),
                ('res_id', '=', overtime.id),
            ]).unlink()
        snapshots = self._presenly_delete_snapshot()
        result = super().unlink()
        self._presenly_write_delete_log(snapshots)
        return result

    def action_delete_with_confirm(self):
        """Server wrapper for the delete button; carries the explicit
        confirmation context required to remove approved requests."""
        return self.with_context(presenly_confirm_delete=True).unlink()
