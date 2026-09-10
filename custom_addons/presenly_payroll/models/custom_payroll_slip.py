import calendar

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CustomPayrollSlip(models.Model):
    _inherit = 'custom.payroll.slip'

    # --- Ringkasan sumber Presenly (computed live, bukan snapshot) ---
    presenly_approved_count = fields.Integer(
        compute='_compute_presenly_overtime',
        string='Approved Overtime Requests',
    )
    presenly_approved_hours = fields.Float(
        compute='_compute_presenly_overtime',
        string='Approved Overtime Hours (Presenly)',
    )
    presenly_approved_request_ids = fields.One2many(
        'presenly.overtime.request',
        compute='_compute_presenly_requests',
        string='Approved Requests',
    )

    def _presenly_approved_requests(self):
        """Live lookup of approved Presenly Overtime Requests inside the
        payroll period. Kept dependency-free (no @api.depends on the overtime
        model) so creating/deleting requests never triggers a SQL search on a
        non-stored computed One2many."""
        if (
            not self.employee_id or not self.payroll_batch_id
            or not self.payroll_batch_id.periode_bulan
            or not self.payroll_batch_id.periode_tahun
        ):
            return self.env['presenly.overtime.request']
        return self.env['presenly.overtime.request'].sudo().search(
            self._presenly_overtime_domain()
        )

    def _compute_presenly_requests(self):
        for rec in self:
            rec.presenly_approved_request_ids = rec._presenly_approved_requests()

    def _compute_presenly_overtime(self):
        for rec in self:
            requests = rec._presenly_approved_requests()
            rec.presenly_approved_count = len(requests)
            rec.presenly_approved_hours = sum(
                requests.mapped('duration_hours') or [0.0]
            )

    @api.model_create_multi
    def create(self, values_list):
        records = super().create(values_list)
        # Sync the 'Auto Overtime' detail right after insert so payslips
        # created through any path (wizard or ORM) already carry the approved
        # Presenly overtime amount. The wizard's own populate step is then
        # idempotent because _sync_auto_overtime_detail reuses the same line.
        for rec in records:
            rec._sync_auto_overtime_detail()
        return records

    def _presenly_overtime_domain(self):
        """Periode payroll: tgl-1 .. akhir bulan (calendar).

        Jika slip punya work_location_id, filter hanya request di lokasi tsb
        (mendukung slip multi-lokasi). Jika null, agregat semua lokasi.
        """
        self.ensure_one()
        year = self.payroll_batch_id.periode_tahun
        month = int(self.payroll_batch_id.periode_bulan)
        start = f'{year}-{month:02d}-01'
        end_day = calendar.monthrange(year, month)[1]
        end = f'{year}-{month:02d}-{end_day:02d}'
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('state', '=', 'approved'),
            ('date', '>=', start),
            ('date', '<=', end),
        ]
        if self.work_location_id:
            domain.append(('work_location_id', '=', self.work_location_id.id))
        return domain

    @api.depends('presenly_approved_hours', 'overtime_override')
    def _compute_attendance_overtime(self):
        """Override: hours ALWAYS from approved Presenly Overtime Requests
        (or manual override). The legacy hr.attendance extra-hours calculation
        is removed entirely."""
        for rec in self:
            rec.attendance_overtime_hours = (
                rec.overtime_override
                if rec.overtime_override and rec.overtime_override > 0
                else rec.presenly_approved_hours
            )

    def _sync_auto_overtime_detail(self):
        """Re-create (or remove) the 'Auto Overtime' detail line so it always
        mirrors the computed overtime amount."""
        self.ensure_one()
        Detail = self.env['custom.payroll.slip.detail']
        existing = self.detail_ids.filtered(
            lambda d: d.component_type == 'lembur'
            and d.description == 'Auto Overtime'
        )
        if self.overtime_amount > 0:
            if existing:
                existing.write({
                    'nominal': self.overtime_amount,
                    'description': self._presenly_overtime_description(),
                })
            else:
                Detail.create({
                    'slip_gaji_id': self.id,
                    'component_type': 'lembur',
                    'nominal': self.overtime_amount,
                    'description': self._presenly_overtime_description(),
                })
        elif existing:
            existing.unlink()

    def _presenly_overtime_description(self):
        count = self.presenly_approved_count
        hours = self.presenly_approved_hours
        if self.overtime_override and self.overtime_override > 0:
            return 'Auto Overtime (manual override %g h)' % self.overtime_override
        return 'Auto Overtime: %d approved request(s) × %g h' % (count, hours)

    def action_refresh_overtime(self):
        """Recompute overtime from approved Presenly requests.

        Protected: paid/cancelled slips are locked so final values never
        change silently.
        """
        for rec in self:
            if rec.status in ('paid', 'cancelled'):
                raise UserError(_(
                    'Cannot refresh overtime on locked slips (paid or cancelled).'
                ))
        self.invalidate_recordset([
            'presenly_approved_count', 'presenly_approved_hours',
            'attendance_overtime_hours', 'overtime_amount',
        ])
        for rec in self:
            rec._sync_auto_overtime_detail()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Overtime Refresh'),
                'message': _('Overtime recalculated from approved Presenly requests.'),
                'type': 'success',
            },
        }