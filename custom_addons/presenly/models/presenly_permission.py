import base64

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PresenlyPermissionType(models.Model):
    _name = 'presenly.permission.type'
    _description = 'Presenly Permission or Dispensation Type'
    _order = 'sequence, name'

    name = fields.Char(translate=True)
    code = fields.Char(index=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, index=True)
    request_mode = fields.Selection([
        ('full_day', 'Full Day / Date Range'),
        ('hours', 'Partial Hours'),
        ('both', 'Full Day or Partial Hours'),
    ], default='both', required=True, string='Allowed Duration')
    requires_attachment = fields.Boolean()
    affects_attendance = fields.Boolean(default=True)
    paid_status = fields.Selection([
        ('paid', 'Paid'), ('unpaid', 'Unpaid'), ('policy', 'According to Policy'),
    ], default='policy', required=True)
    active = fields.Boolean(default=True)
    is_complete = fields.Boolean(compute='_compute_is_complete', store=True)
    approval_route_count = fields.Integer(
        compute='_compute_approval_route_count', compute_sudo=True,
        string='Ready Steps',
    )

    def _compute_approval_route_count(self):
        counts = dict(self.env['presenly.approval.rule']._read_group(
            [
                ('permission_type_id', 'in', self.ids),
                ('active', '=', True),
                ('is_complete', '=', True),
            ],
            ['permission_type_id'],
            ['__count'],
        )) if self.ids else {}
        for permission_type in self:
            permission_type.approval_route_count = counts.get(permission_type, 0)

    def action_open_approval_routes(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_approval_rule'
        )
        action['name'] = f'Approval Route — {self.display_name}'
        action['domain'] = [('permission_type_id', '=', self.id)]
        action['context'] = {
            'default_company_id': self.company_id.id,
            'default_permission_type_id': self.id,
            'default_leave_type_id': False,
        }
        return action

    @api.depends('name', 'code', 'company_id', 'request_mode', 'paid_status')
    def _compute_is_complete(self):
        for permission_type in self:
            permission_type.is_complete = bool(
                permission_type.name
                and permission_type.code
                and permission_type.company_id
                and permission_type.request_mode
                and permission_type.paid_status
            )

    _code_company_unique = models.Constraint(
        'unique(code, company_id)',
        'Permission type code must be unique per company.',
    )


class PresenlyPermission(models.Model):
    _name = 'presenly.permission'
    _description = 'Presenly Permission / Dispensation Request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'presenly.deletion.log.mixin']
    _order = 'create_date desc'

    def _default_employee(self):
        return self.env.user.employee_id

    def _default_work_location(self):
        employee = self.env.user.employee_id
        if not employee:
            return False
        locations = employee._presenly_work_locations_for_period()
        return locations[:1] or employee.work_location_id

    name = fields.Char(default='New', readonly=True, copy=False, index=True)
    employee_id = fields.Many2one(
        'hr.employee', index=True, default=_default_employee, tracking=True,
    )
    company_id = fields.Many2one(related='employee_id.company_id', store=True, index=True)
    work_location_id = fields.Many2one(
        'hr.work.location', index=True, default=_default_work_location,
        tracking=True, check_company=True,
    )
    permission_type_id = fields.Many2one(
        'presenly.permission.type', tracking=True,
    )
    request_mode = fields.Selection([
        ('full_day', 'Full Day / Date Range'),
        ('hours', 'Partial Hours'),
    ], default='full_day', required=True, tracking=True)
    date_from = fields.Date(default=fields.Date.today, tracking=True)
    date_to = fields.Date(default=fields.Date.today, tracking=True)
    hour_from = fields.Float(tracking=True)
    hour_to = fields.Float(tracking=True)
    duration_display = fields.Char(compute='_compute_duration_display')
    reason = fields.Text(tracking=True)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'),
        ('rejected', 'Rejected'), ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True, required=True)
    rejection_reason = fields.Text(readonly=True)
    approval_level = fields.Integer(default=0, readonly=True)
    affects_attendance = fields.Boolean(related='permission_type_id.affects_attendance', store=True)
    paid_status = fields.Selection(related='permission_type_id.paid_status', store=True)
    requires_attachment = fields.Boolean(related='permission_type_id.requires_attachment')
    allowed_request_mode = fields.Selection(related='permission_type_id.request_mode')
    is_request_owner = fields.Boolean(compute='_compute_ui_permissions')
    can_submit = fields.Boolean(compute='_compute_ui_permissions')
    can_approve = fields.Boolean(compute='_compute_ui_permissions')
    can_reject = fields.Boolean(compute='_compute_ui_permissions')
    can_cancel = fields.Boolean(compute='_compute_ui_permissions')

    # UI eligibility flags exposed to the mobile API (readonly computed).
    presenly_can_approve_api = fields.Boolean(
        compute='_compute_presenly_api_flags',
        string='Can Approve (API)',
    )
    presenly_can_reject_api = fields.Boolean(
        compute='_compute_presenly_api_flags',
        string='Can Reject (API)',
    )
    presenly_can_cancel_api = fields.Boolean(
        compute='_compute_presenly_api_flags',
        string='Can Cancel (API)',
    )

    @api.depends_context('uid')
    @api.depends('can_submit', 'can_approve', 'can_reject', 'can_cancel')
    def _compute_presenly_api_flags(self):
        for permission in self:
            permission.presenly_can_approve_api = permission.can_approve
            permission.presenly_can_reject_api = permission.can_reject
            permission.presenly_can_cancel_api = permission.can_cancel

    can_edit_request = fields.Boolean(compute='_compute_ui_permissions')
    current_approver_ids = fields.Many2many('res.users', compute='_compute_ui_permissions')
    presenly_pending_approver_ids = fields.Many2many(
        'res.users', 'presenly_permission_pending_approver_rel',
        'permission_id', 'user_id', string='Pending Approvers',
        readonly=True, copy=False,
    )
    presenly_approver_history_ids = fields.Many2many(
        'res.users', 'presenly_permission_approver_history_rel',
        'permission_id', 'user_id', string='Approver History',
        readonly=True, copy=False,
    )
    approval_progress_display = fields.Char(compute='_compute_approval_progress_display')

    @api.depends('date_from', 'date_to', 'hour_from', 'hour_to', 'request_mode')
    def _compute_duration_display(self):
        for permission in self:
            if permission.request_mode == 'hours':
                duration = max(permission.hour_to - permission.hour_from, 0.0)
                permission.duration_display = f'{duration:g} hours'
            elif permission.date_from and permission.date_to:
                days = (permission.date_to - permission.date_from).days + 1
                permission.duration_display = f'{days} day' if days == 1 else f'{days} days'
            else:
                permission.duration_display = False

    @api.depends_context('uid')
    @api.depends(
        'state', 'employee_id.user_id', 'approval_level', 'work_location_id',
        'permission_type_id', 'presenly_pending_approver_ids',
    )
    def _compute_ui_permissions(self):
        current_user = self.env.user
        is_manager = current_user.has_group('presenly.group_presenly_manager')
        for permission in self:
            owner = permission.employee_id.user_id == current_user
            approvers = self.env['res.users']
            if permission.id and permission.state == 'submitted':
                approvers = permission.presenly_pending_approver_ids
                if not approvers:
                    rule = permission._presenly_current_rule()
                    approvers = rule._approvers_for(permission) if rule else approvers
            is_current_approver = current_user in approvers
            permission.is_request_owner = owner
            permission.current_approver_ids = approvers
            permission.can_submit = permission.state == 'draft' and (owner or is_manager)
            permission.can_approve = permission.state == 'submitted' and is_current_approver
            permission.can_reject = permission.state == 'submitted' and is_current_approver
            permission.can_cancel = bool(permission._origin.id) and permission.state in ('draft', 'submitted') and (owner or is_manager)
            permission.can_edit_request = permission.state == 'draft' and (owner or is_manager)

    @api.depends(
        'state', 'approval_level',
        'presenly_approval_request_id.state',
        'presenly_approval_request_id.current_step_id',
        'presenly_approval_request_id.step_ids.state',
    )
    def _compute_approval_progress_display(self):
        for permission in self:
            approval = permission.presenly_approval_request_id
            if approval:
                permission.approval_progress_display = approval.progress_display
            elif permission.state == 'approved':
                permission.approval_progress_display = 'Approval completed'
            elif permission.state == 'rejected':
                permission.approval_progress_display = 'Rejected'
            elif permission.state == 'cancelled':
                permission.approval_progress_display = 'Cancelled'
            else:
                permission.approval_progress_display = 'Not submitted'

    @api.onchange('permission_type_id')
    def _onchange_permission_type_id(self):
        if self.permission_type_id.request_mode in ('full_day', 'hours'):
            self.request_mode = self.permission_type_id.request_mode

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            if values.get('name', 'New') == 'New':
                values['name'] = self.env['ir.sequence'].next_by_code('presenly.permission') or 'New'
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
            raise UserError('Request status can only be changed using Presenly workflow actions.')
        transaction_fields = {
            'employee_id', 'work_location_id', 'permission_type_id', 'request_mode',
            'date_from', 'date_to', 'hour_from', 'hour_to', 'reason', 'attachment_ids',
        }
        if transaction_fields.intersection(values) and any(record.state != 'draft' for record in self):
            raise UserError('Only draft permission requests can be edited.')
        return super().write(values)

    @api.model
    def create_api_attachments(self, permission, attachments):
        attachment_ids = []
        for item in attachments or []:
            if not isinstance(item, dict) or not item.get('name') or not item.get('data'):
                raise ValidationError('Each attachment requires name and base64 data.')
            try:
                decoded = base64.b64decode(item['data'], validate=True)
            except Exception as error:
                raise ValidationError('Attachment data must be valid base64.') from error
            if len(decoded) > 10 * 1024 * 1024:
                raise ValidationError('Each attachment must not exceed 10 MB.')
            attachment = self.env['ir.attachment'].sudo().create({
                'name': item['name'],
                'type': 'binary',
                'datas': item['data'],
                'mimetype': item.get('mimetype', 'application/octet-stream'),
                'res_model': 'presenly.permission',
                'res_id': permission.id,
                'public': False,
            })
            attachment_ids.append(attachment.id)
        permission.with_context(presenly_workflow=permission.state != 'draft').write({
            'attachment_ids': [(6, 0, attachment_ids)],
        })
        return permission.attachment_ids

    def action_open_reject_wizard(self):
        self.ensure_one()
        self._presenly_check_approver()
        return {
            'type': 'ir.actions.act_window', 'name': 'Reject Permission',
            'res_model': 'presenly.permission.reject.wizard', 'view_mode': 'form',
            'target': 'new', 'context': {'default_permission_id': self.id},
        }

    def unlink(self):
        is_admin = self.env.su or self.env.user.has_group(
            'presenly.group_presenly_manager'
        )
        if not is_admin:
            if not self.env.user.has_group('presenly.group_presenly_hr'):
                raise UserError(
                    'Only a Presenly Administrator or HR Officer can delete '
                    'permission requests.'
                )
            not_hr_ok = self.filtered(
                lambda request: request.state not in
                ('draft', 'rejected', 'cancelled')
            )
            if not_hr_ok:
                raise UserError(
                    'HR can only delete draft, rejected, or cancelled '
                    'permission requests.'
                )
        for permission in self:
            if permission.state == 'approved' and not self.env.context.get(
                'presenly_confirm_delete'
            ):
                raise UserError(
                    'Approved permission requests require explicit '
                    'confirmation before they can be deleted.'
                )
        # Purge children BEFORE unlink so their FKs cannot block the row
        # delete. Everything runs in one transaction: if super().unlink()
        # fails, the whole purge is rolled back.
        for permission in self:
            permission._presenly_purge_approval(keep_logs=True)
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', permission._name),
                ('res_id', '=', permission.id),
            ]).unlink()
            permission.attachment_ids.sudo().unlink()
        snapshots = self._presenly_delete_snapshot()
        result = super().unlink()
        self._presenly_write_delete_log(snapshots)
        return result

    def action_delete_with_confirm(self):
        """Server wrapper for the delete button; carries the explicit
        confirmation context required to remove approved requests."""
        return self.with_context(presenly_confirm_delete=True).unlink()

    @api.constrains('date_from', 'date_to', 'hour_from', 'hour_to', 'request_mode', 'permission_type_id', 'state')
    def _check_dates(self):
        """Drafts may be incomplete because Odoo autosaves them on navigation.

        Complete business validation is performed by ``action_submit``.
        """
        for permission in self:
            if permission.state == 'draft':
                continue
            permission._presenly_validate_submission()

    def action_submit(self):
        self._presenly_validate_submission()
        return super().action_submit() if hasattr(super(), 'action_submit') else True

    def _presenly_validate_submission(self):
        for permission in self:
            missing_fields = []
            if not permission.employee_id:
                missing_fields.append('Employee')
            if not permission.work_location_id:
                missing_fields.append('Work Location')
            elif (
                permission.work_location_id.company_id != permission.company_id
                or permission.work_location_id not in permission.employee_id._presenly_work_locations_for_period(
                    permission.date_from, permission.date_to,
                )
            ):
                missing_fields.append('Work Location scheduled for the requested period')
            if not permission.permission_type_id or not permission.permission_type_id.is_complete:
                missing_fields.append('Valid Permission Type')
            if not permission.date_from:
                missing_fields.append('Start Date')
            if not permission.date_to:
                missing_fields.append('End Date')
            if not (permission.reason or '').strip():
                missing_fields.append('Reason')
            if missing_fields:
                raise ValidationError(
                    'Complete the following fields before submitting: %s.' % ', '.join(missing_fields)
                )
            if permission.date_to < permission.date_from:
                raise ValidationError('End date must be after or equal to start date.')
            if permission.request_mode == 'hours':
                if permission.date_from != permission.date_to:
                    raise ValidationError('A partial-hours request must use the same start and end date.')
                if not 0 <= permission.hour_from < permission.hour_to <= 24:
                    raise ValidationError('Partial hours must have a valid start and end time.')
            allowed_mode = permission.permission_type_id.request_mode
            if allowed_mode != 'both' and permission.request_mode != allowed_mode:
                raise ValidationError('The selected duration mode is not allowed for this permission type.')
            if permission.permission_type_id.requires_attachment and not permission.attachment_ids:
                raise ValidationError('An attachment is required for this permission type.')
        return True

    def action_cancel(self):
        for permission in self:
            if not permission.can_cancel:
                raise UserError('You cannot cancel this permission request.')
        self.with_context(presenly_workflow=True).write({
            'state': 'cancelled',
            'presenly_pending_approver_ids': [(5, 0, 0)],
        })
        return True
