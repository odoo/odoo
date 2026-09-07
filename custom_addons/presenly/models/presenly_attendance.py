import base64
import binascii

from datetime import datetime, timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.image import image_process
from odoo.tools.mimetypes import guess_mimetype


SELFIE_MAX_BYTES = 5 * 1024 * 1024
SELFIE_MIMETYPES = {
    'image/jpeg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}

# HR may hard-delete attendance records only inside this correction window
# (days counted from check_in). Records outside the window must be archived
# by an Administrator instead. Move to ir.config_parameter when policy is final.
PRESENLY_CORRECTION_DAYS = 31


class HrAttendance(models.Model):
    _name = 'hr.attendance'
    _inherit = ['hr.attendance', 'presenly.deletion.log.mixin']

    # The native related field inherits groups from
    # ``hr.employee.attendance_manager_id`` (``group_hr_attendance_officer``),
    # yet ``_compute_is_manager`` (native, called via super) and the
    # group-expand ``_read_group_employee_id`` always read it. Without opening
    # it, any Presenly employee who can see an attendance list triggers an
    # AccessError on this field. Opening it to Presenly Employee keeps the
    # self-service view working while preserving officer-level semantics.
    attendance_manager_id = fields.Many2one(
        'res.users',
        related='employee_id.attendance_manager_id',
        groups='presenly.group_presenly_employee,hr_attendance.group_hr_attendance_officer',
    )

    presenly_company_id = fields.Many2one(
        'res.company', string='Operational Company', index=True, readonly=True,
    )
    presenly_work_location_id = fields.Many2one(
        'hr.work.location', string='Work Location', index=True, readonly=True,
        check_company=True,
    )
    presenly_schedule_id = fields.Many2one(
        'presenly.work.location.schedule', string='Work Location Schedule',
        index=True, readonly=True, ondelete='set null',
    )
    presenly_check_in_distance = fields.Float(readonly=True)
    presenly_check_out_distance = fields.Float(readonly=True)
    presenly_check_in_accuracy = fields.Float(
        compute='_compute_presenly_event_details',
        string='Check-In GPS Accuracy (m)', compute_sudo=True,
    )
    presenly_check_out_accuracy = fields.Float(
        compute='_compute_presenly_event_details',
        string='Check-Out GPS Accuracy (m)', compute_sudo=True,
    )
    presenly_selfie_in_attachment_id = fields.Many2one('ir.attachment', readonly=True)
    presenly_selfie_out_attachment_id = fields.Many2one('ir.attachment', readonly=True)
    presenly_selfie_in_image = fields.Binary(
        related='presenly_selfie_in_attachment_id.datas',
        string='Check-In Selfie', readonly=True,
    )
    presenly_selfie_out_image = fields.Binary(
        related='presenly_selfie_out_attachment_id.datas',
        string='Check-Out Selfie', readonly=True,
    )
    presenly_can_change_employee = fields.Boolean(
        compute='_compute_presenly_can_change_employee',
    )
    presenly_can_delete = fields.Boolean(
        compute='_compute_presenly_can_delete',
    )
    presenly_source = fields.Selection([
        ('mobile', 'Mobile'), ('web', 'Web'), ('manual', 'Manual'),
    ], default='manual', readonly=True)
    presenly_attendance_mode = fields.Selection([
        ('location', 'On-Site'),
        ('wfa', 'Work From Anywhere'),
    ], string='Attendance Mode', default='location', index=True, readonly=True)
    presenly_event_ids = fields.One2many(
        'presenly.attendance.event', 'attendance_id', string='Attendance Evidence',
    )
    presenly_evidence_count = fields.Integer(
        compute='_compute_presenly_evidence_count', string='Evidence Count',
    )

    @api.depends(
        'check_in', 'check_out', 'worked_hours', 'out_mode',
        'presenly_source', 'presenly_work_location_id',
        'presenly_attendance_mode',
        'presenly_event_ids.event_type',
        'presenly_event_ids.validation_status',
    )
    def _compute_color(self):
        """Use Presenly evidence semantics for mobile attendance colors.

        Native Odoo marks every technical checkout red. Presenly deliberately
        uses technical mode for its server-owned mobile timestamps, so a
        completed and evidenced mobile session is valid (green), not an error.
        Non-Presenly records retain the native Odoo color behavior.
        """
        super()._compute_color()
        stale_before = datetime.today() - timedelta(days=1)
        for attendance in self.filtered(lambda record: record.presenly_source == 'mobile'):
            successful_events = attendance.sudo().presenly_event_ids.filtered(
                lambda event: event.validation_status == 'success'
            )
            has_check_in = any(
                event.event_type == 'check_in' for event in successful_events
            )
            has_check_out = any(
                event.event_type == 'check_out' for event in successful_events
            )
            requires_work_location = attendance.presenly_attendance_mode != 'wfa'
            invalid = (
                (requires_work_location and not attendance.presenly_work_location_id)
                or not has_check_in
                or (attendance.check_out and not has_check_out)
                or (attendance.check_out and attendance.worked_hours > 16)
                or (not attendance.check_out and attendance.check_in < stale_before)
            )
            attendance.color = 1 if invalid else 10

    @api.depends('presenly_event_ids')
    def _compute_presenly_evidence_count(self):
        grouped = self.env['presenly.attendance.event']._read_group(
            [('attendance_id', 'in', self.ids)],
            ['attendance_id'],
            ['__count'],
        ) if self.ids else []
        count_by_attendance = {attendance.id: count for attendance, count in grouped}
        for attendance in self:
            attendance.presenly_evidence_count = count_by_attendance.get(attendance.id, 0)

    @api.depends(
        'presenly_event_ids.event_type',
        'presenly_event_ids.validation_status',
        'presenly_event_ids.accuracy',
    )
    def _compute_presenly_event_details(self):
        for attendance in self:
            successful = attendance.presenly_event_ids.filtered(
                lambda event: event.validation_status == 'success'
            )
            check_in_event = successful.filtered(
                lambda event: event.event_type == 'check_in'
            )[:1]
            check_out_event = successful.filtered(
                lambda event: event.event_type == 'check_out'
            )[:1]
            attendance.presenly_check_in_accuracy = check_in_event.accuracy or 0.0
            attendance.presenly_check_out_accuracy = check_out_event.accuracy or 0.0

    @api.model
    def _presenly_user_can_change_employee(self):
        """Presenly HR may reassign records; Employee/Approver may not.

        Some Presenly users also need a native Attendance group to open the
        Attendances shell. That native group must not turn the Employee field
        into an effective reassignment control for employee self-service.
        """
        if self.env.su:
            return True
        user = self.env.user
        if user.has_group('presenly.group_presenly_hr'):
            return True
        if user.has_group('presenly.group_presenly_employee'):
            return False
        return user.has_group('hr_attendance.group_hr_attendance_user')

    @api.depends_context('uid')
    def _compute_presenly_can_change_employee(self):
        allowed = self._presenly_user_can_change_employee()
        for attendance in self:
            attendance.presenly_can_change_employee = allowed

    @api.depends_context('uid')
    def _compute_presenly_can_delete(self):
        allowed = self._presenly_hr_or_admin_can_delete()
        for attendance in self:
            attendance.presenly_can_delete = allowed

    @api.depends('employee_id')
    def _compute_is_manager(self):
        super()._compute_is_manager()
        if not self._presenly_user_can_change_employee():
            for attendance in self:
                attendance.is_manager = False

    @api.model_create_multi
    def create(self, values_list):
        """Reject manual/UI/RPC creation; mobile uses a private server method."""
        raise ValidationError(_(
            'Attendance records can only be created through Presenly check-in. '
            'Open Attendance History to review existing records.'
        ))

    @api.model
    def _presenly_mobile_create(self, values):
        """Private server-only entry point used after mobile validation.

        Leading-underscore model methods cannot be invoked through Odoo RPC.
        """
        return super().create(values)

    def _update_overtime(self, attendance_domain=None):
        """Disable the native automatic overtime generation.

        Overtime / lembur is managed by Presenly requests
        (``presenly.overtime.request``) with explicit datetime ranges and meal
        allowance; the native engine that derives ``hr.attendance.overtime.line``
        from check-in/out must not run, so the only source of overtime is the
        Presenly request flow. Existing native lines are left untouched.
        """
        return True

    def action_approve_overtime(self):
        raise ValidationError(_(
            'Native Extra Hours approval is disabled. Overtime is managed by '
            'Presenly Overtime requests.'
        ))

    def action_refuse_overtime(self):
        raise ValidationError(_(
            'Native Extra Hours refusal is disabled. Overtime is managed by '
            'Presenly Overtime requests.'
        ))

    def write(self, values):
        protected_fields = {
            'employee_id', 'check_in', 'check_out',
            'presenly_company_id', 'presenly_work_location_id',
            'presenly_schedule_id', 'presenly_check_in_distance',
            'presenly_check_out_distance', 'presenly_selfie_in_attachment_id',
            'presenly_selfie_out_attachment_id', 'presenly_source',
            'presenly_attendance_mode',
            'in_latitude', 'in_longitude', 'in_location', 'in_ip_address',
            'in_browser', 'in_mode', 'out_latitude', 'out_longitude',
            'out_location', 'out_ip_address', 'out_browser', 'out_mode',
        }
        if protected_fields.intersection(values):
            raise ValidationError(_(
                'Attendance history is read-only. Check-in and check-out can '
                'only be recorded through the Presenly mobile application.'
            ))
        return super().write(values)

    def _presenly_mobile_checkout(self, values):
        """Private server-only checkout of a validated Presenly session."""
        self.ensure_one()
        if self.presenly_source != 'mobile':
            raise ValidationError(_('Only a Presenly mobile attendance can use this checkout.'))
        allowed_fields = {
            'check_out', 'presenly_check_out_distance',
            'presenly_selfie_out_attachment_id', 'out_latitude',
            'out_longitude', 'out_mode',
        }
        if set(values) - allowed_fields:
            raise ValidationError(_('Invalid fields in the Presenly mobile checkout.'))
        return super().write(values)

    def _presenly_migration_write(self, values):
        """Private server-only write for idempotent native-structure backfill.

        Leading-underscore methods cannot be invoked through Odoo RPC. This
        narrow method exists so migration backfill does not collide with the
        intentional Attendance history read-only guard.
        """
        allowed_fields = {
            'presenly_company_id', 'presenly_work_location_id',
            'presenly_schedule_id',
        }
        if set(values) - allowed_fields:
            raise ValidationError(_('Invalid fields in Attendance migration write.'))
        return super().write(values)

    def unlink(self):
        blocked = self._presenly_delete_blocked_reason()
        if blocked:
            raise ValidationError(blocked)
        snapshots = self._presenly_delete_snapshot()
        for attendance in self:
            attendance._presenly_purge_children()
        result = super().unlink()
        self._presenly_write_delete_log(snapshots)
        return result

    def _presenly_delete_blocked_reason(self):
        """Return a human-readable reason when the current user cannot delete
        these records, or an empty string when deletion is allowed.

        Admin: allowed.
        HR: allowed only inside the correction window and when the attendance
        is not backing an approved overtime request.
        """
        if self.env.su:
            return ''
        user = self.env.user
        if user.has_group('presenly.group_presenly_manager'):
            return ''
        if not user.has_group('presenly.group_presenly_hr'):
            return _(
                'Only a Presenly Administrator or HR Officer can delete '
                'attendance history.'
            )
        now = fields.Datetime.now()
        for attendance in self:
            if attendance.presenly_has_overtime_evidence():
                return _(
                    'This attendance is the basis of an approved overtime '
                    'request and cannot be deleted by HR. Ask an '
                    'Administrator if the request is no longer needed.'
                )
            if attendance.check_in and (
                now - attendance.check_in
            ) > timedelta(days=PRESENLY_CORRECTION_DAYS):
                return _(
                    'This attendance is older than the %(days)d-day '
                    'correction window.',
                    days=PRESENLY_CORRECTION_DAYS,
                )
        return ''

    def _presenly_hr_or_admin_can_delete(self):
        """Admin can delete anything. HR is limited to a short correction
        window (PRESENLY_CORRECTION_DAYS from check_in) and cannot delete
        attendance that backs an overtime request."""
        return not bool(self._presenly_delete_blocked_reason())

    def presenly_has_overtime_evidence(self):
        self.ensure_one()
        return bool(self.env['presenly.overtime.request'].sudo().search_count([
            ('employee_id', '=', self.employee_id.id),
            ('date', '=', self.check_in.date()),
            ('state', 'in', ('submitted', 'approved')),
        ], limit=1))

    def _presenly_purge_children(self):
        """Remove evidence events and their private selfie attachments so
        no orphan records remain after the attendance row disappears."""
        events = self.presenly_event_ids
        attachments = (
            events.mapped('selfie_attachment_id')
            | self.presenly_selfie_in_attachment_id
            | self.presenly_selfie_out_attachment_id
        )
        attachments.sudo().unlink()
        events.sudo().with_context(
            presenly_skip_deletion_log=True
        ).unlink()

    def action_presenly_delete(self):
        """Form delete button for Attendance.

        The button is always shown to HR/Administrator; ``unlink()`` answers
        with a specific rejection reason when the record is outside policy
        (e.g. older than the correction window or backing an overtime request).
        """
        return self.unlink()

    def action_open_presenly_evidence(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id(
            'presenly.action_presenly_attendance_event'
        )
        action['domain'] = [('attendance_id', '=', self.id)]
        action['context'] = {
            'default_attendance_id': self.id,
            'default_employee_id': self.employee_id.id,
            'create': False,
        }
        return action


class PresenlyAttendanceEvent(models.Model):
    _name = 'presenly.attendance.event'
    _description = 'Presenly Attendance Evidence Event'
    _inherit = ['mail.thread', 'presenly.deletion.log.mixin']
    _order = 'event_time desc'

    employee_id = fields.Many2one(
        'hr.employee', required=True, index=True, ondelete='cascade', tracking=True,
    )
    company_id = fields.Many2one(
        related='employee_id.company_id', store=True, readonly=True, index=True,
    )
    attendance_id = fields.Many2one(
        'hr.attendance', index=True, ondelete='set null', tracking=True,
    )
    event_type = fields.Selection([
        ('check_in', 'Check In'), ('check_out', 'Check Out'),
    ], required=True, index=True, tracking=True)
    event_time = fields.Datetime(
        required=True, default=fields.Datetime.now, index=True, tracking=True,
    )
    latitude = fields.Float(digits=(10, 7), tracking=True)
    longitude = fields.Float(digits=(10, 7), tracking=True)
    accuracy = fields.Float(tracking=True)
    distance_from_location = fields.Float(tracking=True)
    work_location_id = fields.Many2one(
        'hr.work.location', index=True, tracking=True, check_company=True,
    )
    schedule_id = fields.Many2one(
        'presenly.work.location.schedule', string='Work Location Schedule',
        index=True, readonly=True, ondelete='set null',
    )
    attendance_mode = fields.Selection([
        ('location', 'On-Site'),
        ('wfa', 'Work From Anywhere'),
    ], string='Attendance Mode', index=True, readonly=True)
    selfie_attachment_id = fields.Many2one(
        'ir.attachment', readonly=True, ondelete='set null',
    )
    selfie_image = fields.Binary(
        related='selfie_attachment_id.datas', string='Selfie', readonly=True,
    )
    source = fields.Selection([
        ('mobile', 'Mobile'), ('web', 'Web'), ('manual', 'Manual'),
    ], required=True, default='mobile', tracking=True)
    validation_status = fields.Selection([
        ('success', 'Success'), ('failed', 'Failed'),
    ], required=True, tracking=True)
    validation_message = fields.Char(tracking=True)
    device_id_hash = fields.Char(index=True, readonly=True)

    def write(self, values):
        auditable_fields = {
            'event_time', 'source', 'validation_status', 'validation_message',
            'distance_from_location', 'accuracy', 'work_location_id',
            'latitude', 'longitude',
        }
        changed_fields = auditable_fields.intersection(values)
        result = super().write(values)
        if changed_fields and not self.env.context.get('presenly_skip_manual_audit'):
            field_labels = [self._fields[name].string for name in sorted(changed_fields)]
            for event in self:
                event.message_post(
                    body=self.env._(
                        'Attendance evidence was manually updated. Changed fields: %(fields)s',
                        fields=', '.join(field_labels),
                    ),
                    subtype_xmlid='mail.mt_note',
                )
        return result

    def unlink(self):
        is_admin = self.env.su or self.env.user.has_group(
            'presenly.group_presenly_manager'
        )
        if not is_admin:
            if not self.env.user.has_group('presenly.group_presenly_hr'):
                raise UserError(
                    'Only a Presenly Administrator or HR Officer can delete '
                    'attendance evidence.'
                )
            forbidden = self.filtered(
                lambda event: event.validation_status == 'success'
                and event.attendance_id
            )
            if forbidden:
                raise UserError(
                    'HR can only delete failed evidence or evidence of a '
                    'deleted attendance. Successful check-in/out evidence is '
                    'kept; ask an Administrator to remove the attendance '
                    'record instead.'
                )
        if self.env.context.get('presenly_skip_deletion_log'):
            return super().unlink()
        snapshots = self._presenly_delete_snapshot()
        result = super().unlink()
        self._presenly_write_delete_log(snapshots)
        return result

    @api.model
    def create_failed_event(self, employee, event_type, payload=None, message=None):
        payload = payload or {}
        values = {
            'employee_id': employee.id,
            'event_type': event_type,
            'source': 'mobile',
            'validation_status': 'failed',
            'validation_message': message,
        }
        mode = payload.get('attendance_mode')
        if mode in ('location', 'wfa'):
            values['attendance_mode'] = mode
        location_id = payload.get('work_location_id') or payload.get('unit_id')
        if location_id:
            try:
                location = self.env['hr.work.location'].browse(int(location_id)).exists()
                if location and location.company_id == employee.company_id:
                    values['work_location_id'] = location.id
            except (TypeError, ValueError):
                pass
        for field_name in ('latitude', 'longitude', 'accuracy'):
            value = payload.get(field_name)
            if value not in (None, ''):
                try:
                    values[field_name] = float(value)
                except (TypeError, ValueError):
                    pass
        return self.create(values)

    @api.model
    def validate_selfie(self, selfie):
        """Decode and validate a private mobile attendance selfie.

        The API deliberately accepts only raw base64 (not a data URL), limits
        decoded bytes before attachment creation, verifies the actual file
        signature, and lets Odoo/Pillow reject invalid or excessive images.
        """
        if not selfie:
            raise ValidationError('Selfie is required for this attendance event.')
        if not isinstance(selfie, str):
            raise ValidationError('selfie must be base64 text.')
        if selfie.startswith('data:'):
            raise ValidationError(
                'selfie must not include a data URL prefix; send raw base64 only.'
            )
        # Base64 expands data by roughly 4/3. Reject oversized encoded input
        # before allocating the decoded byte array.
        maximum_encoded_length = ((SELFIE_MAX_BYTES + 2) // 3) * 4
        if len(selfie) > maximum_encoded_length:
            raise ValidationError('Selfie image must not exceed 5 MB.')
        try:
            raw = base64.b64decode(selfie, validate=True)
        except (binascii.Error, ValueError, UnicodeEncodeError) as error:
            raise ValidationError('Selfie must be valid base64 data.') from error
        if not raw:
            raise ValidationError('Selfie image must not be empty.')
        if len(raw) > SELFIE_MAX_BYTES:
            raise ValidationError('Selfie image must not exceed 5 MB.')
        mimetype = guess_mimetype(raw, default='application/octet-stream')
        if mimetype not in SELFIE_MIMETYPES:
            raise ValidationError('Selfie must be a JPEG, PNG, or WebP image.')
        try:
            image_process(raw, verify_resolution=True)
        except (UserError, ValueError, OSError) as error:
            raise ValidationError('Selfie could not be decoded as a safe image.') from error
        return raw, mimetype, SELFIE_MIMETYPES[mimetype]

    @api.model
    def create_selfie_attachment(self, employee, selfie, event_type):
        raw, mimetype, extension = self.validate_selfie(selfie)
        return self.env['ir.attachment'].sudo().create({
            'name': f'presenly_{event_type}_{employee.id}.{extension}',
            'type': 'binary',
            'datas': base64.b64encode(raw),
            'mimetype': mimetype,
            'res_model': 'presenly.attendance.event',
            'public': False,
        })
