from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PresenlyApprovalRule(models.Model):
    _name = 'presenly.approval.rule'
    _description = 'Presenly Approval Route Step'
    _order = 'company_id, sequence, work_location_id, id'

    name = fields.Char()
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company, index=True,
    )
    work_location_id = fields.Many2one(
        'hr.work.location', index=True, check_company=True,
    )
    permission_type_id = fields.Many2one(
        'presenly.permission.type', string='Permission Type', index=True,
    )
    leave_type_id = fields.Many2one(
        'hr.leave.type', string='Time Off Type', index=True,
    )
    is_overtime_route = fields.Boolean(
        string='Overtime Route', default=False,
        help='When set, this step approves Presenly Overtime requests for the '
             'company/work location scope (no request type required).',
    )
    sequence = fields.Integer(default=10, string='Order')
    approver_type = fields.Selection([
        ('user', 'Specific User'),
        ('employee_manager', 'Employee Manager'),
        ('unit_manager', 'Work Location Manager'),
        ('hr', 'HR Officer'),
        ('group', 'Odoo Group'),
    ], required=True, default='unit_manager', string='Approver Source')
    approver_user_id = fields.Many2one('res.users')
    approver_group_id = fields.Many2one('res.groups')
    # Kept for schema compatibility. Every configured level is required in the
    # single Presenly approval path.
    required = fields.Boolean(default=True)
    active = fields.Boolean(default=True)
    is_complete = fields.Boolean(compute='_compute_is_complete', store=True)
    request_type_display = fields.Char(
        compute='_compute_route_display', string='Request Type',
    )
    scope_display = fields.Char(
        compute='_compute_route_display', string='Work Location Scope',
    )
    approver_display = fields.Char(
        compute='_compute_route_display', string='Approver Source',
    )

    @api.depends(
        'permission_type_id', 'permission_type_id.name',
        'leave_type_id', 'leave_type_id.name', 'work_location_id',
        'work_location_id.name', 'approver_type', 'approver_user_id',
        'approver_user_id.name', 'approver_group_id', 'approver_group_id.name',
        'is_overtime_route',
    )
    def _compute_route_display(self):
        approver_labels = dict(self._fields['approver_type'].selection)
        for rule in self:
            if rule.is_overtime_route:
                rule.request_type_display = 'Overtime'
            elif rule.permission_type_id:
                rule.request_type_display = (
                    f'Permission: {rule.permission_type_id.display_name}'
                )
            elif rule.leave_type_id:
                rule.request_type_display = (
                    f'Time Off: {rule.leave_type_id.display_name}'
                )
            else:
                rule.request_type_display = 'Select a request type'

            rule.scope_display = (
                rule.work_location_id.display_name
                if rule.work_location_id
                else 'All Work Locations (Company Default)'
            )
            if rule.approver_type == 'user' and rule.approver_user_id:
                rule.approver_display = rule.approver_user_id.display_name
            elif rule.approver_type == 'group' and rule.approver_group_id:
                rule.approver_display = rule.approver_group_id.display_name
            else:
                rule.approver_display = approver_labels.get(
                    rule.approver_type, 'Select an approver source'
                )

    @api.depends(
        'name', 'company_id', 'work_location_id',
        'permission_type_id', 'permission_type_id.is_complete', 'leave_type_id',
        'approver_type', 'approver_user_id', 'approver_group_id',
        'is_overtime_route',
    )
    def _compute_is_complete(self):
        for rule in self:
            if rule.is_overtime_route:
                target_is_valid = True
            else:
                target_is_valid = bool(
                    (rule.permission_type_id and rule.permission_type_id.is_complete)
                    or rule.leave_type_id
                )
            approver_is_valid = rule.approver_type not in ('user', 'group')
            if rule.approver_type == 'user':
                approver_is_valid = bool(rule.approver_user_id)
            elif rule.approver_type == 'group':
                approver_is_valid = bool(rule.approver_group_id)
            rule.is_complete = bool(
                rule.name
                and rule.company_id
                and target_is_valid
                and (
                    rule.is_overtime_route
                    or bool(rule.permission_type_id) != bool(rule.leave_type_id)
                )
                and (
                    not rule.work_location_id
                    or rule.work_location_id.company_id == rule.company_id
                )
                and approver_is_valid
            )

    @api.constrains(
        'company_id', 'work_location_id', 'permission_type_id',
        'leave_type_id', 'is_overtime_route', 'sequence', 'active',
    )
    def _check_unique_level_scope(self):
        for rule in self.filtered('active'):
            if rule.is_overtime_route and (rule.permission_type_id or rule.leave_type_id):
                raise ValidationError(
                    'An overtime approval step must not target a Permission Type '
                    'or a Time Off Type.'
                )
            if rule.permission_type_id and rule.leave_type_id:
                raise ValidationError(
                    'An approval step must target either a Permission Type or '
                    'a Time Off Type, not both.'
                )
            if rule.sequence < 0:
                raise ValidationError('Approval level sequence cannot be negative.')
            domain = [
                ('id', '!=', rule.id),
                ('active', '=', True),
                ('company_id', '=', rule.company_id.id),
                ('work_location_id', '=', rule.work_location_id.id or False),
                ('permission_type_id', '=', rule.permission_type_id.id or False),
                ('leave_type_id', '=', rule.leave_type_id.id or False),
                ('is_overtime_route', '=', rule.is_overtime_route),
                ('sequence', '=', rule.sequence),
            ]
            if self.search_count(domain):
                raise ValidationError(
                    'Only one approval step may use the same Order for the '
                    'same company, location, and request type.'
                )

    def _get_rules(self, request, request_kind):
        """Resolve one deterministic chain for the target request.

        Company-wide and location-specific levels may be combined. If both use
        the same sequence, the location-specific level overrides the global
        level. This lets HR define a common chain and replace selected levels at
        a school/site without accidentally creating duplicate levels.
        """
        domain = [
            ('company_id', '=', request.company_id.id),
            ('active', '=', True),
            ('is_complete', '=', True),
        ]
        if request_kind == 'leave':
            domain += [
                ('permission_type_id', '=', False),
                ('leave_type_id', '=', request.holiday_status_id.id),
            ]
        elif request_kind == 'overtime':
            domain += [
                ('permission_type_id', '=', False),
                ('leave_type_id', '=', False),
                ('is_overtime_route', '=', True),
            ]
        else:
            domain += [
                ('leave_type_id', '=', False),
                ('permission_type_id', '=', request.permission_type_id.id),
            ]
        location = (
            getattr(request, 'presenly_work_location_id', False)
            or getattr(request, 'work_location_id', False)
        )
        domain += [
            ('work_location_id', 'in', [False, location.id] if location else [False]),
        ]
        candidates = self.sudo().search(domain, order='sequence, id')
        by_sequence = defaultdict(lambda: self.env['presenly.approval.rule'])
        for rule in candidates:
            by_sequence[rule.sequence] |= rule

        resolved = self.env['presenly.approval.rule']
        for sequence in sorted(by_sequence):
            levels = by_sequence[sequence]
            specific = levels.filtered(lambda item: item.work_location_id == location)
            selected = specific or levels.filtered(lambda item: not item.work_location_id)
            if len(selected) != 1:
                raise ValidationError(
                    f'Approval Order {sequence} is ambiguous. Keep only one '
                    'matching step for this company, location, and request type.'
                )
            resolved |= selected
        return resolved

    def _approvers_for(self, request):
        self.ensure_one()
        users = self.env['res.users']
        if self.approver_type == 'user':
            users = self.approver_user_id.sudo()
        elif self.approver_type == 'employee_manager':
            employee = request.employee_id.sudo()
            users = employee.parent_id.user_id or employee.leave_manager_id
        elif self.approver_type == 'unit_manager':
            location = (
                getattr(request, 'presenly_work_location_id', False)
                or getattr(request, 'work_location_id', False)
            )
            users = location.sudo().presenly_manager_id if location else users
        elif self.approver_type == 'hr':
            users = self.env.ref(
                'hr_holidays.group_hr_holidays_responsible'
            ).sudo().users
        elif self.approver_type == 'group':
            users = self.approver_group_id.sudo().users
        return users.filtered(
            lambda user: user.active and request.company_id in user.company_ids
        )

    def _validate_flow(self, request):
        if not self:
            request_label = getattr(
                request, 'permission_type_id', False
            ) or getattr(request, 'holiday_status_id', False)
            fallback_label = 'this request type'
            if request._name == 'presenly.overtime.request':
                fallback_label = 'Overtime'
            raise UserError(
                'No complete Presenly Approval Route is configured for '
                f'{request_label.display_name if request_label else fallback_label} at '
                f'{request.company_id.display_name}.'
            )
        for level, rule in enumerate(self, start=1):
            approvers = rule._approvers_for(request)
            if not approvers:
                raise UserError(
                    f'Approval step {level} ({rule.display_name}) has no active '
                    'approver in the request company. Complete the Approval Route '
                    'before submitting.'
                )
            missing_role = approvers.filtered(
                lambda user: not user.has_group(
                    'presenly.group_presenly_approver'
                )
            )
            if missing_role:
                raise UserError(
                    f'Approval step {level} ({rule.display_name}) assigns '
                    f'{", ".join(missing_role.mapped("name"))}, but they do not '
                    'have the Presenly Approver role. Grant the role before '
                    'submitting requests.'
                )
        return True


class PresenlyApprovalRequest(models.Model):
    _name = 'presenly.approval.request'
    _description = 'Presenly Approval Journey'
    _order = 'create_date desc, id desc'

    name = fields.Char(compute='_compute_display_fields', string='Request')
    target_model = fields.Selection([
        ('presenly.permission', 'Permission / Dispensation'),
        ('hr.leave', 'Time Off'),
        ('presenly.overtime.request', 'Overtime / Lembur'),
    ], required=True, index=True, readonly=True)
    target_res_id = fields.Integer(required=True, index=True, readonly=True)
    target_display_name = fields.Char(
        compute='_compute_display_fields', string='Target',
    )
    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True, readonly=True,
    )
    company_id = fields.Many2one(
        'res.company', required=True, index=True, readonly=True,
    )
    work_location_id = fields.Many2one(
        'hr.work.location', index=True, readonly=True, check_company=True,
    )
    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], required=True, default='pending', index=True, readonly=True)
    step_ids = fields.One2many(
        'presenly.approval.step', 'approval_request_id',
        string='Approval Journey', readonly=True,
    )

    _target_unique = models.Constraint(
        'unique(target_model, target_res_id)',
        'A request can only have one Presenly approval journey.',
    )
    current_step_id = fields.Many2one(
        'presenly.approval.step', readonly=True, ondelete='set null',
    )
    current_approver_ids = fields.Many2many(
        'res.users', compute='_compute_display_fields', string='Current Approvers',
    )
    progress_display = fields.Char(
        compute='_compute_display_fields', string='Progress',
    )
    started_at = fields.Datetime(
        required=True, default=fields.Datetime.now, readonly=True,
    )
    completed_at = fields.Datetime(readonly=True)

    @api.depends(
        'target_model', 'target_res_id', 'state', 'current_step_id',
        'current_step_id.assigned_user_ids', 'step_ids.state',
    )
    def _compute_display_fields(self):
        model_labels = dict(self._fields['target_model'].selection)
        for approval in self:
            target = approval._target_record()
            target_name = target.display_name if target else 'Deleted request'
            approval.target_display_name = target_name
            approval.name = f'{model_labels.get(approval.target_model)} - {target_name}'
            approval.current_approver_ids = (
                approval.current_step_id.assigned_user_ids
                if approval.state == 'pending' else self.env['res.users']
            )
            total = len(approval.step_ids)
            completed = len(approval.step_ids.filtered(
                lambda step: step.state == 'approved'
            ))
            if approval.state == 'pending' and approval.current_step_id:
                approval.progress_display = (
                    f'Level {approval.current_step_id.level} of {total}'
                )
            elif approval.state == 'approved':
                approval.progress_display = f'Completed ({completed}/{total})'
            elif approval.state == 'rejected':
                approval.progress_display = 'Rejected'
            else:
                approval.progress_display = 'Cancelled'

    def _target_record(self):
        self.ensure_one()
        if not self.target_model or not self.target_res_id:
            return self.env[self.target_model] if self.target_model else False
        return self.env[self.target_model].sudo().browse(
            self.target_res_id
        ).exists()

    @api.model
    def _create_for_target(self, target, rules):
        target.ensure_one()
        rules._validate_flow(target)
        location = (
            getattr(target, 'presenly_work_location_id', False)
            or getattr(target, 'work_location_id', False)
        )
        approval = self.sudo().create({
            'target_model': target._name,
            'target_res_id': target.id,
            'employee_id': target.employee_id.id,
            'company_id': target.company_id.id,
            'work_location_id': location.id,
        })
        steps = self.env['presenly.approval.step']
        for level, rule in enumerate(rules, start=1):
            approvers = rule._approvers_for(target)
            steps |= self.env['presenly.approval.step'].sudo().create({
                'approval_request_id': approval.id,
                'level': level,
                'sequence': rule.sequence,
                'name': rule.name,
                'source_rule_id': rule.id,
                'assigned_user_ids': [(6, 0, approvers.ids)],
                'state': 'waiting',
            })
        first_step = steps.sorted(lambda step: (step.level, step.id))[:1]
        first_step._engine_write({'state': 'pending'})
        approval._engine_write({'current_step_id': first_step.id})
        return approval

    def _engine_write(self, values):
        return super(PresenlyApprovalRequest, self.sudo()).write(values)

    def write(self, values):
        raise UserError(
            'Approval journeys are immutable and can only be changed by the '
            'Presenly workflow engine.'
        )

    def unlink(self):
        # Only the internal cascade triggered while deleting a target request
        # may remove an approval journey. Direct deletion is blocked.
        if not self.env.context.get('presenly_cascade_delete') and not self.env.su:
            raise UserError('Approval journeys cannot be deleted directly.')
        return super().unlink()

    def _lock(self):
        self.ensure_one()
        self.env.cr.execute(
            'SELECT id FROM presenly_approval_request WHERE id = %s FOR UPDATE',
            (self.id,),
        )
        self.invalidate_recordset()

    def _check_current_approver(self, actor=None):
        self.ensure_one()
        actor = actor or self.env.user
        approval = self.sudo()
        if approval.state != 'pending' or not approval.current_step_id:
            raise UserError('This approval journey is no longer pending.')
        if actor not in approval.current_step_id.assigned_user_ids:
            raise UserError('You are not an approver for the current level.')
        return approval.current_step_id

    def _approve_current(self, note=False):
        self.ensure_one()
        actor = self.env.user
        approval = self.sudo()
        approval._lock()
        current = approval._check_current_approver(actor=actor)
        current._engine_write({
            'state': 'approved',
            'decision_user_id': actor.id,
            'decision_date': fields.Datetime.now(),
            'decision_note': note or False,
        })
        next_step = approval.step_ids.filtered(
            lambda step: step.state == 'waiting'
        ).sorted(lambda step: (step.level, step.id))[:1]
        if next_step:
            next_step._engine_write({'state': 'pending'})
            approval._engine_write({'current_step_id': next_step.id})
            return next_step, False
        approval._engine_write({
            'state': 'approved',
            'current_step_id': False,
            'completed_at': fields.Datetime.now(),
        })
        return self.env['presenly.approval.step'], True

    def _reject_current(self, reason):
        self.ensure_one()
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError('A rejection reason is required.')
        actor = self.env.user
        approval = self.sudo()
        approval._lock()
        current = approval._check_current_approver(actor=actor)
        current._engine_write({
            'state': 'rejected',
            'decision_user_id': actor.id,
            'decision_date': fields.Datetime.now(),
            'decision_note': reason,
        })
        approval.step_ids.filtered(
            lambda step: step.state == 'waiting'
        )._engine_write({'state': 'cancelled'})
        approval._engine_write({
            'state': 'rejected',
            'current_step_id': False,
            'completed_at': fields.Datetime.now(),
        })
        return current

    def _cancel_pending(self):
        self.ensure_one()
        approval = self.sudo()
        approval._lock()
        if approval.state != 'pending':
            raise UserError('Only a pending approval journey can be cancelled.')
        approval.step_ids.filtered(
            lambda step: step.state in ('waiting', 'pending')
        )._engine_write({'state': 'cancelled'})
        approval._engine_write({
            'state': 'cancelled',
            'current_step_id': False,
            'completed_at': fields.Datetime.now(),
        })
        return True

    def action_open_target(self):
        self.ensure_one()
        target = self._target_record()
        if not target:
            raise UserError('The target request no longer exists.')
        return {
            'type': 'ir.actions.act_window',
            'name': target.display_name,
            'res_model': self.target_model,
            'res_id': target.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def action_open_my_approvals(self):
        candidates = self.sudo().search([
            ('state', '=', 'pending'),
            ('company_id', 'in', self.env.companies.ids),
        ])
        pending = candidates.filtered(
            lambda approval: self.env.user in approval.current_approver_ids
        )
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_my_approvals'
        )
        action['domain'] = [('id', 'in', pending.ids)]
        return action


class PresenlyApprovalStep(models.Model):
    _name = 'presenly.approval.step'
    _description = 'Presenly Approval Journey Step'
    _order = 'approval_request_id, level, id'

    approval_request_id = fields.Many2one(
        'presenly.approval.request', required=True, ondelete='cascade',
        index=True, readonly=True,
    )
    company_id = fields.Many2one(
        related='approval_request_id.company_id', store=True, index=True,
    )
    level = fields.Integer(required=True, readonly=True)
    sequence = fields.Integer(required=True, readonly=True)
    name = fields.Char(required=True, readonly=True)
    source_rule_id = fields.Many2one(
        'presenly.approval.rule', readonly=True, ondelete='set null',
    )
    assigned_user_ids = fields.Many2many(
        'res.users', 'presenly_approval_step_user_rel',
        'step_id', 'user_id', string='Assigned Approvers', readonly=True,
    )
    state = fields.Selection([
        ('waiting', 'Waiting'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], required=True, default='waiting', index=True, readonly=True)
    decision_user_id = fields.Many2one(
        'res.users', string='Decision By', readonly=True,
    )
    decision_date = fields.Datetime(readonly=True)
    decision_note = fields.Text(readonly=True)

    def _engine_write(self, values):
        return super(PresenlyApprovalStep, self.sudo()).write(values)

    def write(self, values):
        raise UserError(
            'Approval steps are immutable and can only be changed by the '
            'Presenly workflow engine.'
        )

    def unlink(self):
        # Only the internal cascade triggered while deleting a target request
        # may remove an approval step. Direct deletion is blocked.
        if not self.env.context.get('presenly_cascade_delete') and not self.env.su:
            raise UserError('Approval steps cannot be deleted directly.')
        return super().unlink()


class PresenlyApprovalLog(models.Model):
    _name = 'presenly.approval.log'
    _description = 'Presenly Approval Decision Log'
    _order = 'decision_date desc'

    request_model = fields.Selection([
        ('presenly.permission', 'Permission'),
        ('hr.leave', 'Time Off'),
        ('presenly.overtime.request', 'Overtime / Lembur'),
    ], required=True, index=True)
    request_res_id = fields.Integer(required=True, index=True)
    level = fields.Integer(required=True)
    approver_id = fields.Many2one('res.users', required=True, index=True)
    decision = fields.Selection([
        ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], required=True)
    note = fields.Text()
    employee_id = fields.Many2one('hr.employee', readonly=True, index=True)
    company_id = fields.Many2one('res.company', readonly=True, index=True)
    decision_date = fields.Datetime(
        default=fields.Datetime.now, required=True, readonly=True,
    )

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            request_model = values.get('request_model')
            request_res_id = values.get('request_res_id')
            if request_model and request_res_id:
                request = self.env[request_model].browse(request_res_id).exists()
                if request:
                    values.setdefault('employee_id', request.employee_id.id)
                    values.setdefault('company_id', request.company_id.id)
        return super().create(values_list)


class PresenlyPermissionApproval(models.Model):
    _inherit = 'presenly.permission'

    presenly_approval_request_id = fields.Many2one(
        'presenly.approval.request', string='Approval Journey',
        readonly=True, copy=False, ondelete='restrict',
    )
    presenly_approval_step_ids = fields.One2many(
        'presenly.approval.step', compute='_compute_presenly_approval_steps',
        string='Approval Steps',
    )

    @api.depends('presenly_approval_request_id.step_ids')
    def _compute_presenly_approval_steps(self):
        for permission in self:
            permission.presenly_approval_step_ids = (
                permission.presenly_approval_request_id.step_ids
            )

    def _presenly_workflow_write(self, values):
        return self.with_context(presenly_workflow=True).write(values)

    def _presenly_rules(self):
        return self.env['presenly.approval.rule']._get_rules(self, 'permission')

    def _presenly_pending_approver_users(self):
        self.ensure_one()
        if self.presenly_approval_request_id:
            return self.presenly_approval_request_id.current_approver_ids
        return self.presenly_pending_approver_ids

    def _presenly_check_approver(self):
        self.ensure_one()
        if self.state != 'submitted' or not self.presenly_approval_request_id:
            raise UserError('Only submitted permission requests can be approved.')
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
        for permission in self:
            approval = permission.presenly_approval_request_id
            if approval.state != 'pending' or not approval.current_step_id:
                continue
            for user in approval.current_approver_ids:
                permission.activity_schedule(
                    activity_type_xmlid,
                    user_id=user.id,
                    note=(
                        f'Permission approval {approval.progress_display}: '
                        f'{permission.display_name}'
                    ),
                )

    @api.model
    def _presenly_backfill_approval_requests(self):
        permissions = self.sudo().search([
            ('state', '=', 'submitted'),
            ('presenly_approval_request_id', '=', False),
        ])
        for permission in permissions:
            rules = permission._presenly_rules()
            if not rules:
                continue
            try:
                approval = self.env[
                    'presenly.approval.request'
                ]._create_for_target(permission, rules)
            except UserError:
                continue
            permission._presenly_workflow_write({
                'presenly_approval_request_id': approval.id,
                'approval_level': 0,
                'presenly_pending_approver_ids': [
                    (6, 0, approval.current_approver_ids.ids),
                ],
                'presenly_approver_history_ids': [
                    (6, 0, approval.current_approver_ids.ids),
                ],
            })
        return True

    @api.model
    def _presenly_backfill_pending_approvers(self):
        self._presenly_backfill_approval_requests()
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
            'presenly.action_presenly_permission_approvals'
        )
        action['domain'] = [('id', 'in', pending.ids)]
        return action

    def action_submit(self):
        for permission in self:
            if not permission.can_submit or permission.state != 'draft':
                raise UserError('Only an authorized draft request can be submitted.')
            permission._presenly_validate_submission()
            if self.search_count([
                ('id', '!=', permission.id),
                ('employee_id', '=', permission.employee_id.id),
                ('state', 'in', ('submitted', 'approved')),
                ('date_from', '<=', permission.date_to),
                ('date_to', '>=', permission.date_from),
            ]):
                raise ValidationError(
                    'This permission overlaps another submitted or approved request.'
                )
            rules = permission._presenly_rules()
            approval = self.env[
                'presenly.approval.request'
            ]._create_for_target(permission, rules)
            approvers = approval.current_approver_ids
            permission._presenly_workflow_write({
                'state': 'submitted',
                'approval_level': 0,
                'rejection_reason': False,
                'presenly_approval_request_id': approval.id,
                'presenly_pending_approver_ids': [(6, 0, approvers.ids)],
                'presenly_approver_history_ids': [(6, 0, approvers.ids)],
            })
            permission._presenly_notify_current_approvers()
        return True

    def action_presenly_approve(self):
        for permission in self:
            current = permission._presenly_check_approver()
            current_users = current.assigned_user_ids
            next_step, completed = (
                permission.presenly_approval_request_id._approve_current()
            )
            self.env['presenly.approval.log'].sudo().create({
                'request_model': 'presenly.permission',
                'request_res_id': permission.id,
                'level': current.level,
                'approver_id': self.env.user.id,
                'decision': 'approved',
            })
            permission._presenly_close_approval_activities(current_users)
            if completed:
                permission._presenly_workflow_write({
                    'state': 'approved',
                    'approval_level': len(
                        permission.presenly_approval_request_id.step_ids
                    ),
                    'presenly_pending_approver_ids': [(5, 0, 0)],
                })
            else:
                permission._presenly_workflow_write({
                    'approval_level': next_step.level - 1,
                    'presenly_pending_approver_ids': [
                        (6, 0, next_step.assigned_user_ids.ids),
                    ],
                    'presenly_approver_history_ids': [
                        (4, user_id) for user_id in next_step.assigned_user_ids.ids
                    ],
                })
                permission._presenly_notify_current_approvers()
        return True

    def action_approve(self):
        return self.action_presenly_approve()

    def action_presenly_reject(self, reason):
        reason = (reason or '').strip()
        if not reason:
            raise ValidationError('A rejection reason is required.')
        for permission in self:
            current = permission._presenly_check_approver()
            current_users = current.assigned_user_ids
            permission.presenly_approval_request_id._reject_current(reason)
            self.env['presenly.approval.log'].sudo().create({
                'request_model': 'presenly.permission',
                'request_res_id': permission.id,
                'level': current.level,
                'approver_id': self.env.user.id,
                'decision': 'rejected',
                'note': reason,
            })
            permission._presenly_close_approval_activities(current_users)
            permission._presenly_workflow_write({
                'state': 'rejected',
                'rejection_reason': reason,
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
        return True

    def action_reject(self, reason):
        return self.action_presenly_reject(reason)

    def action_cancel(self):
        for permission in self:
            if not permission.can_cancel:
                raise UserError('You cannot cancel this permission request.')
            if permission.presenly_approval_request_id:
                permission.presenly_approval_request_id._cancel_pending()
            permission._presenly_close_approval_activities(
                permission.presenly_pending_approver_ids
            )
            permission._presenly_workflow_write({
                'state': 'cancelled',
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
        return True


class HrLeaveTypePresenly(models.Model):
    _inherit = 'hr.leave.type'

    presenly_approval_engine = fields.Selection([
        ('presenly', 'Presenly Approval Routes'),
    ], required=True, default='presenly', readonly=True, copy=False)
    presenly_approval_route_count = fields.Integer(
        compute='_compute_presenly_approval_route_count', compute_sudo=True,
        string='Ready Steps',
    )

    def _compute_presenly_approval_route_count(self):
        counts = dict(self.env['presenly.approval.rule']._read_group(
            [
                ('leave_type_id', 'in', self.ids),
                ('active', '=', True),
                ('is_complete', '=', True),
            ],
            ['leave_type_id'],
            ['__count'],
        )) if self.ids else {}
        for leave_type in self:
            leave_type.presenly_approval_route_count = counts.get(leave_type, 0)

    def action_open_presenly_approval_routes(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_approval_rule'
        )
        action['name'] = f'Approval Route — {self.display_name}'
        action['domain'] = [('leave_type_id', '=', self.id)]
        action['context'] = {
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_leave_type_id': self.id,
            'default_permission_type_id': False,
        }
        return action

    @api.model_create_multi
    def create(self, values_list):
        for values in values_list:
            values['presenly_approval_engine'] = 'presenly'
            values['leave_validation_type'] = 'hr'
        return super().create(values_list)

    def write(self, values):
        if values.get('presenly_approval_engine') not in (None, 'presenly'):
            raise UserError('Time Off approval is managed by Presenly Approval Routes.')
        if values.get('leave_validation_type') not in (None, 'hr'):
            raise UserError(
                'Native Time Off approval cannot be enabled because Presenly '
                'Approval Routes are the single approval path.'
            )
        values = dict(values)
        values['presenly_approval_engine'] = 'presenly'
        values['leave_validation_type'] = 'hr'
        return super().write(values)

    @api.model
    def _presenly_enable_single_approval_flow(self):
        types = self.with_context(active_test=False).sudo().search([])
        if types:
            super(HrLeaveTypePresenly, types).write({
                'presenly_approval_engine': 'presenly',
                'leave_validation_type': 'hr',
            })
        return True


class HrLeavePresenly(models.Model):
    _name = 'hr.leave'
    _inherit = ['hr.leave', 'presenly.deletion.log.mixin']

    presenly_work_location_id = fields.Many2one(
        'hr.work.location', string='Work Location', index=True, tracking=True,
        check_company=True,
    )
    presenly_approval_engine = fields.Selection(
        related='holiday_status_id.presenly_approval_engine', readonly=True,
    )
    presenly_approval_level = fields.Integer(
        default=0, readonly=True, copy=False, tracking=True,
    )
    presenly_approval_state = fields.Selection([
        ('not_started', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], default='not_started', readonly=True, copy=False, tracking=True)
    presenly_rejection_reason = fields.Text(readonly=True, copy=False)
    presenly_pending_approver_ids = fields.Many2many(
        'res.users', 'presenly_leave_pending_approver_rel',
        'leave_id', 'user_id', string='Pending Approvers',
        readonly=True, copy=False,
    )
    presenly_approver_history_ids = fields.Many2many(
        'res.users', 'presenly_leave_approver_history_rel',
        'leave_id', 'user_id', string='Approver History',
        readonly=True, copy=False,
    )
    presenly_approval_request_id = fields.Many2one(
        'presenly.approval.request', string='Approval Journey',
        readonly=True, copy=False, ondelete='restrict',
    )
    presenly_approval_step_ids = fields.One2many(
        'presenly.approval.step', compute='_compute_presenly_approval_steps',
        string='Approval Steps',
    )
    presenly_approval_progress = fields.Char(
        related='presenly_approval_request_id.progress_display', readonly=True,
    )
    presenly_current_approver_ids = fields.Many2many(
        related='presenly_approval_request_id.current_approver_ids', readonly=True,
    )
    presenly_can_submit = fields.Boolean(compute='_compute_presenly_ui_permissions')
    presenly_can_approve = fields.Boolean(compute='_compute_presenly_ui_permissions')
    presenly_can_reject = fields.Boolean(compute='_compute_presenly_ui_permissions')
    presenly_can_cancel = fields.Boolean(compute='_compute_presenly_ui_permissions')
    presenly_can_edit = fields.Boolean(compute='_compute_presenly_ui_permissions')

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
    @api.depends(
        'presenly_can_approve', 'presenly_can_reject', 'presenly_can_cancel',
    )
    def _compute_presenly_api_flags(self):
        for leave in self:
            leave.presenly_can_approve_api = leave.presenly_can_approve
            leave.presenly_can_reject_api = leave.presenly_can_reject
            leave.presenly_can_cancel_api = leave.presenly_can_cancel

    # Native approval buttons must not appear for Presenly-managed Time Off.
    # Force all native can_* flags to False; server guards still reject RPC.
    def _presenly_is_managed(self):
        return self.presenly_approval_engine == 'presenly'

    def _compute_can_approve(self):
        super()._compute_can_approve()
        for leave in self:
            if leave._presenly_is_managed():
                leave.can_approve = False

    def _compute_can_validate(self):
        super()._compute_can_validate()
        for leave in self:
            if leave._presenly_is_managed():
                leave.can_validate = False

    def _compute_can_refuse(self):
        super()._compute_can_refuse()
        for leave in self:
            if leave._presenly_is_managed():
                leave.can_refuse = False

    def _compute_can_back_to_approve(self):
        super()._compute_can_back_to_approve()
        for leave in self:
            if leave._presenly_is_managed():
                leave.can_back_to_approve = False

    @api.depends('presenly_approval_request_id.step_ids')
    def _compute_presenly_approval_steps(self):
        for leave in self:
            leave.presenly_approval_step_ids = leave.presenly_approval_request_id.step_ids

    @api.depends_context('uid')
    @api.depends(
        'state', 'presenly_approval_state', 'employee_id.user_id',
        'presenly_approval_request_id.current_step_id.assigned_user_ids',
    )
    def _compute_presenly_ui_permissions(self):
        user = self.env.user
        is_manager = user.has_group('presenly.group_presenly_manager')
        for leave in self:
            owner = leave.employee_id.user_id == user
            pending_approvers = leave.presenly_approval_request_id.current_approver_ids
            leave.presenly_can_submit = bool(
                leave.id
                and leave.state in ('draft', 'confirm')
                and leave.presenly_approval_state == 'not_started'
                and (owner or is_manager)
            )
            leave.presenly_can_approve = bool(
                leave.presenly_approval_state == 'pending'
                and user in pending_approvers
            )
            leave.presenly_can_reject = leave.presenly_can_approve
            leave.presenly_can_cancel = bool(
                leave.id
                and leave.presenly_approval_state in ('not_started', 'pending')
                and (owner or is_manager)
            )
            leave.presenly_can_edit = bool(
                leave.presenly_approval_state == 'not_started'
                and leave.state in ('draft', 'confirm')
                and (owner or is_manager)
            )

    @api.model_create_multi
    def create(self, values_list):
        protected = {
            'presenly_approval_level', 'presenly_approval_state',
            'presenly_rejection_reason', 'presenly_pending_approver_ids',
            'presenly_approver_history_ids', 'presenly_approval_request_id',
        }
        clean_values = []
        for values in values_list:
            values = dict(values)
            for field_name in protected:
                values.pop(field_name, None)
            values['presenly_approval_state'] = 'not_started'
            clean_values.append(values)
        return super(
            HrLeavePresenly,
            self.with_context(mail_activity_automation_skip=True),
        ).create(clean_values)

    def _presenly_workflow_write(self, values):
        return super(HrLeavePresenly, self.sudo()).write(values)

    def write(self, values):
        protected = {
            'presenly_approval_level', 'presenly_approval_state',
            'presenly_rejection_reason', 'presenly_pending_approver_ids',
            'presenly_approver_history_ids', 'presenly_approval_request_id',
        }
        if protected.intersection(values):
            raise UserError(
                'Presenly approval fields can only be changed using workflow actions.'
            )
        transaction_fields = {
            'employee_id', 'holiday_status_id', 'presenly_work_location_id',
            'request_date_from', 'request_date_to', 'request_hour_from',
            'request_hour_to', 'request_date_from_period',
            'request_date_to_period', 'name', 'supported_attachment_ids',
        }
        if transaction_fields.intersection(values) and any(
            leave.presenly_approval_state != 'not_started' for leave in self
        ):
            raise UserError(
                'A Time Off request cannot be edited after it enters Presenly approval.'
            )
        if 'state' in values:
            target_state = values['state']
            invalid = self.filtered(lambda leave: (
                target_state == 'validate'
                and (
                    leave.presenly_approval_state != 'approved'
                    or leave.presenly_approval_request_id.state != 'approved'
                )
            ) or (
                target_state == 'refuse'
                and (
                    leave.presenly_approval_state != 'rejected'
                    or leave.presenly_approval_request_id.state != 'rejected'
                )
            ) or (
                target_state == 'validate1'
            ))
            if invalid:
                raise UserError(
                    'Time Off approval and rejection must follow the Presenly '
                    'Approval Journey.'
                )
        return super().write(values)

    def _presenly_rules(self):
        return self.env['presenly.approval.rule']._get_rules(self, 'leave')

    def _presenly_pending_approver_users(self):
        self.ensure_one()
        if self.presenly_approval_request_id:
            return self.presenly_approval_request_id.current_approver_ids
        return self.presenly_pending_approver_ids

    def _presenly_check_approver(self):
        self.ensure_one()
        if (
            self.presenly_approval_state != 'pending'
            or not self.presenly_approval_request_id
        ):
            raise UserError('Only a pending Time Off request can be approved.')
        self.presenly_approval_request_id._check_current_approver()
        return self.presenly_approval_request_id.current_step_id

    def _presenly_close_approval_activities(self, users):
        activity_type = self.env.ref(
            'hr_holidays.mail_act_leave_approval', raise_if_not_found=False,
        )
        if activity_type and users:
            self.env['mail.activity'].sudo().search([
                ('res_model', '=', self._name),
                ('res_id', '=', self.id),
                ('activity_type_id', '=', activity_type.id),
                ('user_id', 'in', users.ids),
            ]).unlink()

    def _presenly_notify_current_approvers(self):
        activity_type_xmlid = 'hr_holidays.mail_act_leave_approval'
        if not self.env.ref(activity_type_xmlid, raise_if_not_found=False):
            return
        for leave in self:
            approval = leave.presenly_approval_request_id
            if approval.state != 'pending' or not approval.current_step_id:
                continue
            for user in approval.current_approver_ids:
                leave.activity_schedule(
                    activity_type_xmlid,
                    user_id=user.id,
                    note=(
                        f'Time Off approval {approval.progress_display}: '
                        f'{leave.display_name}'
                    ),
                )

    @api.model
    def _presenly_backfill_approval_requests(self):
        leaves = self.sudo().search([
            ('presenly_approval_state', '=', 'pending'),
            ('presenly_approval_request_id', '=', False),
        ])
        for leave in leaves:
            rules = leave._presenly_rules()
            if not rules:
                continue
            try:
                approval = self.env[
                    'presenly.approval.request'
                ]._create_for_target(leave, rules)
            except UserError:
                continue
            leave._presenly_workflow_write({
                'presenly_approval_request_id': approval.id,
                'presenly_approval_level': 0,
                'presenly_pending_approver_ids': [
                    (6, 0, approval.current_approver_ids.ids),
                ],
                'presenly_approver_history_ids': [
                    (6, 0, approval.current_approver_ids.ids),
                ],
            })
        return True

    @api.model
    def _presenly_backfill_pending_approvers(self):
        self._presenly_backfill_approval_requests()
        return True

    @api.model
    def action_open_presenly_approval_queue(self):
        candidates = self.search([
            ('presenly_approval_state', '=', 'pending'),
            ('company_id', 'in', self.env.companies.ids),
        ])
        pending = candidates.filtered(
            lambda leave: self.env.user in leave._presenly_pending_approver_users()
        )
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_leave_approvals'
        )
        action['domain'] = [('id', 'in', pending.ids)]
        return action

    def action_presenly_submit(self):
        for leave in self:
            if not leave.presenly_can_submit:
                raise UserError('You cannot submit this Time Off request.')
            scheduled_locations = leave.employee_id._presenly_work_locations_for_period(
                leave.request_date_from, leave.request_date_to,
            )
            if (
                not leave.presenly_work_location_id
                or leave.presenly_work_location_id.company_id != leave.company_id
                or leave.presenly_work_location_id not in scheduled_locations
            ):
                raise UserError(
                    'Select a Work Location scheduled for the employee during '
                    'the Time Off period.'
                )
            rules = leave._presenly_rules()
            approval = self.env[
                'presenly.approval.request'
            ]._create_for_target(leave, rules)
            approvers = approval.current_approver_ids
            leave._presenly_workflow_write({
                'presenly_approval_level': 0,
                'presenly_approval_state': 'pending',
                'presenly_rejection_reason': False,
                'presenly_approval_request_id': approval.id,
                'presenly_pending_approver_ids': [(6, 0, approvers.ids)],
                'presenly_approver_history_ids': [(6, 0, approvers.ids)],
            })
            leave._presenly_notify_current_approvers()
        return True

    def action_presenly_approve(self):
        for leave in self:
            current = leave._presenly_check_approver()
            current_users = current.assigned_user_ids
            next_step, completed = leave.presenly_approval_request_id._approve_current()
            self.env['presenly.approval.log'].sudo().create({
                'request_model': 'hr.leave',
                'request_res_id': leave.id,
                'level': current.level,
                'approver_id': self.env.user.id,
                'decision': 'approved',
            })
            leave._presenly_close_approval_activities(current_users)
            if not completed:
                leave._presenly_workflow_write({
                    'presenly_approval_level': next_step.level - 1,
                    'presenly_pending_approver_ids': [
                        (6, 0, next_step.assigned_user_ids.ids),
                    ],
                    'presenly_approver_history_ids': [
                        (4, user_id) for user_id in next_step.assigned_user_ids.ids
                    ],
                })
                leave._presenly_notify_current_approvers()
                continue

            actor_employee = self.env.user.employee_id
            leave._presenly_workflow_write({
                'presenly_approval_state': 'approved',
                'presenly_approval_level': len(
                    leave.presenly_approval_request_id.step_ids
                ),
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
            # Native Odoo remains the final transaction engine for allocations,
            # resource calendar leaves, duration, and work entries.
            super(HrLeavePresenly, leave.sudo())._action_validate(
                check_state=False
            )
            if actor_employee:
                leave._presenly_workflow_write({
                    'first_approver_id': actor_employee.id,
                })
        return True

    def action_presenly_open_reject_wizard(self):
        self.ensure_one()
        self._presenly_check_approver()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Time Off Request',
            'res_model': 'presenly.leave.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_leave_id': self.id},
        }

    def action_presenly_reject(self, reason=False):
        reason = (reason or self.env.context.get('rejection_reason') or '').strip()
        if not reason:
            raise ValidationError('A rejection reason is required.')
        for leave in self:
            current = leave._presenly_check_approver()
            current_users = current.assigned_user_ids
            leave.presenly_approval_request_id._reject_current(reason)
            self.env['presenly.approval.log'].sudo().create({
                'request_model': 'hr.leave',
                'request_res_id': leave.id,
                'level': current.level,
                'approver_id': self.env.user.id,
                'decision': 'rejected',
                'note': reason,
            })
            leave._presenly_close_approval_activities(current_users)
            leave._presenly_workflow_write({
                'state': 'refuse',
                'presenly_approval_state': 'rejected',
                'presenly_rejection_reason': reason,
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
            leave.activity_update()
        return True

    def action_presenly_cancel(self):
        for leave in self:
            if not leave.presenly_can_cancel:
                raise UserError('You cannot cancel this Time Off request.')
            if leave.presenly_approval_request_id:
                leave.presenly_approval_request_id._cancel_pending()
            leave._presenly_close_approval_activities(
                leave.presenly_pending_approver_ids
            )
            leave._presenly_workflow_write({
                'state': 'cancel',
                'presenly_approval_state': 'cancelled',
                'presenly_pending_approver_ids': [(5, 0, 0)],
            })
        return True

    def _force_cancel(
        self, reason=None, msg_subtype='mail.mt_comment',
        notify_responsibles=True,
    ):
        managed = self.filtered(
            lambda leave: leave.presenly_approval_engine == 'presenly'
        )
        if managed.filtered(
            lambda leave: leave.presenly_approval_state in ('not_started', 'pending')
        ):
            raise UserError(
                'Use Cancel Request to cancel a pending Presenly Approval Journey.'
            )
        result = super()._force_cancel(
            reason=reason,
            msg_subtype=msg_subtype,
            notify_responsibles=notify_responsibles,
        )
        managed._presenly_workflow_write({
            'presenly_approval_state': 'cancelled',
            'presenly_pending_approver_ids': [(5, 0, 0)],
        })
        return result

    def unlink(self):
        snapshots = self._presenly_delete_snapshot()
        self._presenly_purge_approval(keep_logs=True)
        result = super().unlink()
        self._presenly_write_delete_log(snapshots)
        return result

    def action_presenly_delete(self):
        """List header delete button for Time Off.

        The native ``hr.leave`` ondelete guard already limits which states may
        be deleted per role; our override purges the Presenly approval journey
        and records the deletion audit entry.
        """
        return self.unlink()

    def action_approve(self, check_state=True):
        if self.filtered(lambda leave: leave.presenly_approval_engine == 'presenly'):
            raise UserError(
                'Time Off approval is managed by Presenly Approval Routes. '
                'Open My Approvals and process the current level.'
            )
        return super().action_approve(check_state=check_state)

    def _action_validate(self, check_state=True):
        invalid = self.filtered(lambda leave: (
            leave.presenly_approval_engine == 'presenly'
            and (
                leave.presenly_approval_state != 'approved'
                or leave.presenly_approval_request_id.state != 'approved'
            )
        ))
        if invalid:
            raise UserError(
                'Time Off cannot be validated before its Presenly Approval '
                'Journey is complete.'
            )
        return super()._action_validate(check_state=check_state)

    def action_refuse(self):
        if self.filtered(lambda leave: leave.presenly_approval_engine == 'presenly'):
            raise UserError(
                'Time Off rejection is managed by Presenly Approval Routes. '
                'Use Reject and provide a reason on the current approval step.'
            )
        return super().action_refuse()

    def action_back_to_approval(self):
        if self.filtered(lambda leave: leave.presenly_approval_engine == 'presenly'):
            raise UserError(
                'Presenly-managed Time Off cannot be returned to native approval.'
            )
        return super().action_back_to_approval()
