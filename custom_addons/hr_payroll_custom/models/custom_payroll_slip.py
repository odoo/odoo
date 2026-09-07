from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from datetime import date, datetime
import calendar


class CustomPayrollSlip(models.Model):
    _name = 'custom.payroll.slip'
    _description = 'Payslip'
    _order = 'employee_id, payroll_batch_id'
    _inherit = ['mail.thread.main.attachment', 'mail.activity.mixin']

    name = fields.Char(string='Slip Number', readonly=True, copy=False, default='New')
    payroll_batch_id = fields.Many2one('custom.payroll.batch', string='Payroll Batch', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='restrict')
    employee_name = fields.Char(related='employee_id.name', string='Employee Name', store=True)
    department_id = fields.Many2one(related='employee_id.department_id', string='Department', store=True)
    job_id = fields.Many2one(related='employee_id.job_id', string='Job Position', store=True)
    contract_wage = fields.Monetary(
        related='employee_id.version_id.contract_wage',
        string='Contract Wage',
        currency_field='currency_id',
    )
    total_gaji_pokok = fields.Monetary(
        string='Basic Salary',
        currency_field='currency_id',
        default=0.0,
        help='Total gaji pokok yang digunakan sebagai dasar perhitungan BPJS &amp; komponen lain. '
             'Otomatis terisi dari contract wage karyawan saat employee dipilih. '
             'Sekali payslip dibuat, nilai ini menjadi snapshot untuk seluruh kalkulasi.',
    )
    total_tunjangan = fields.Monetary(string='Total Allowances', currency_field='currency_id', compute='_compute_totals', store=True)
    total_potongan = fields.Monetary(string='Total Deductions', currency_field='currency_id', compute='_compute_totals', store=True)
    total_lembur = fields.Monetary(string='Total Overtime', currency_field='currency_id', compute='_compute_totals', store=True)
    total_earnings = fields.Monetary(
        string='Total Earnings (Gross)',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
        help='Gross earnings = Basic Salary + Total Allowances + Total Overtime.',
    )
    total_pendapatan = fields.Monetary(string='Take Home Pay (Net)', currency_field='currency_id', compute='_compute_totals', store=True)

    batch_status = fields.Selection(
        related='payroll_batch_id.status',
        string='Batch Status',
        readonly=True,
    )
    batch_submitter_id = fields.Many2one(
        related='payroll_batch_id.submitter_id',
        string='Batch Submitter',
        readonly=True,
    )
    batch_approver_id = fields.Many2one(
        related='payroll_batch_id.approver_id',
        string='Batch Approver',
        readonly=True,
    )
    batch_approval_date = fields.Datetime(
        related='payroll_batch_id.approval_date',
        string='Batch Approval Date',
        readonly=True,
    )
    batch_rejection_reason = fields.Text(
        related='payroll_batch_id.rejection_reason',
        string='Batch Rejection Reason',
        readonly=True,
    )
    detail_ids = fields.One2many('custom.payroll.slip.detail', 'slip_gaji_id', string='Details')
    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('paid', 'Paid'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )
    email_status = fields.Selection(
        selection=[
            ('not_sent', 'Not Sent'),
            ('sent', 'Sent'),
            ('failed', 'Failed'),
            ('skipped', 'Skipped'),
        ],
        string='Email Status',
        default='not_sent',
        required=True,
        tracking=True,
        copy=False,
    )
    email_sent_at = fields.Datetime(string='Email Sent At', readonly=True, copy=False)
    email_sent_by = fields.Many2one(
        'res.users', string='Email Sent By', readonly=True, copy=False
    )
    email_error = fields.Text(string='Email Error', readonly=True, copy=False)
    email_mail_id = fields.Many2one(
        'mail.mail', string='Email Record', readonly=True, copy=False
    )
    email_delivery_state = fields.Selection(
        related='email_mail_id.state', string='Delivery State', readonly=True
    )
    email_delivery_error = fields.Text(
        related='email_mail_id.failure_reason', string='Delivery Error', readonly=True
    )
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    def _check_payroll_officer(self):
        if not self.env.user.has_group('hr_payroll_custom.group_payroll_user'):
            raise AccessError(_('Only Payroll Officers or Administrators can manage payslips.'))

    def _check_payroll_manager(self):
        if not self.env.user.has_group('hr_payroll_custom.group_payroll_manager'):
            raise AccessError(_('Only Payroll Administrators can perform this action.'))

    attendance_overtime_hours = fields.Float(
        string='Overtime Hours (from Attendance)',
        compute='_compute_attendance_overtime',
        store=True,
        help='Total jam lembur dari hr.attendance selama periode payroll. '
             'Threshold: jam kerja > overtime_threshold_hours per hari dihitung lembur.',
    )
    overtime_threshold_hours = fields.Float(
        string='Daily Threshold (hours)',
        default=8.0,
        help='Batas jam kerja normal per hari. Kelebihannya dihitung lembur.',
    )
    overtime_rate = fields.Float(
        string='Overtime Rate Multiplier',
        default=1.5,
        help='Pengali lembur. Contoh: 1.5 = 1.5x gaji per jam.',
    )
    overtime_override = fields.Float(
        string='Manual Overtime Hours Override',
        default=0.0,
        help='Jika diisi > 0, override hasil auto dari attendance. '
             'Set 0 untuk pakai auto-calculation.',
    )
    hourly_rate = fields.Monetary(
        string='Hourly Rate',
        currency_field='currency_id',
        compute='_compute_hourly_rate',
        help='Gaji per jam = contract wage / 173 (asumsi 173 jam kerja/bulan).',
    )
    overtime_amount = fields.Monetary(
        string='Calculated Overtime',
        currency_field='currency_id',
        compute='_compute_overtime_amount',
        store=True,
        help='Nilai lembur = jam lembur x hourly rate x rate multiplier.',
    )

    @api.depends('detail_ids.nominal', 'detail_ids.component_type', 'total_gaji_pokok', 'overtime_amount')
    def _compute_totals(self):
        for rec in self:
            tunjangan = sum(rec.detail_ids.filtered(lambda d: d.component_type == 'tunjangan').mapped('nominal'))
            rule_add = sum(rec.detail_ids.filtered(
                lambda d: d.component_type == 'rule' and (d.rule_id.category_id.code == 'ALW')
            ).mapped('nominal'))
            rule_ded = sum(rec.detail_ids.filtered(
                lambda d: d.component_type == 'rule' and (d.rule_id.category_id.code == 'DED')
            ).mapped('nominal'))
            potongan = sum(rec.detail_ids.filtered(lambda d: d.component_type == 'potongan').mapped('nominal'))
            lembur = rec.overtime_amount
            bpjs = sum(rec.detail_ids.filtered(lambda d: d.component_type == 'bpjs').mapped('nominal'))

            rec.total_tunjangan = tunjangan + rule_add
            rec.total_potongan = potongan + bpjs + rule_ded
            rec.total_lembur = lembur
            rec.total_earnings = (
                rec.total_gaji_pokok + tunjangan + rule_add + lembur
            )
            rec.total_pendapatan = (
                rec.total_gaji_pokok + tunjangan + rule_add + lembur - potongan - bpjs - rule_ded
            )

    @api.depends('payroll_batch_id.periode_bulan', 'payroll_batch_id.periode_tahun',
                 'employee_id', 'overtime_threshold_hours', 'overtime_override')
    def _compute_attendance_overtime(self):
        Attendance = self.env['hr.attendance']
        for rec in self:
            if rec.overtime_override and rec.overtime_override > 0:
                rec.attendance_overtime_hours = rec.overtime_override
                continue
            if not rec.employee_id or not rec.payroll_batch_id.periode_bulan or not rec.payroll_batch_id.periode_tahun:
                rec.attendance_overtime_hours = 0.0
                continue
            year = rec.payroll_batch_id.periode_tahun
            month = int(rec.payroll_batch_id.periode_bulan)
            try:
                start_date = date(year, month, 1)
                _, last_day = calendar.monthrange(year, month)
                end_date = date(year, month, last_day)
            except (ValueError, TypeError):
                rec.attendance_overtime_hours = 0.0
                continue
            start_dt = datetime.combine(start_date, datetime.min.time())
            end_dt = datetime.combine(end_date, datetime.max.time())
            attendances = Attendance.search([
                ('employee_id', '=', rec.employee_id.id),
                ('check_in', '>=', start_dt),
                ('check_in', '<=', end_dt),
            ])
            overtime = 0.0
            for att in attendances:
                if att.worked_hours and att.worked_hours > rec.overtime_threshold_hours:
                    overtime += att.worked_hours - rec.overtime_threshold_hours
            rec.attendance_overtime_hours = overtime

    @api.depends('total_gaji_pokok')
    def _compute_hourly_rate(self):
        for rec in self:
            if rec.total_gaji_pokok:
                rec.hourly_rate = rec.total_gaji_pokok / 173.0
            else:
                rec.hourly_rate = 0.0

    @api.depends('attendance_overtime_hours', 'hourly_rate', 'overtime_rate')
    def _compute_overtime_amount(self):
        for rec in self:
            rec.overtime_amount = rec.attendance_overtime_hours * rec.hourly_rate * rec.overtime_rate

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                batch_id = vals.get('payroll_batch_id')
                seq_code = 'custom.payroll.slip'
                if batch_id:
                    batch = self.env['custom.payroll.batch'].browse(batch_id)
                    if batch.company_id:
                        seq_code = 'custom.payroll.slip.{}'.format(batch.company_id.id)
                sequence = self.env['ir.sequence'].next_by_code(seq_code)
                if not sequence and seq_code != 'custom.payroll.slip':
                    sequence = self.env['ir.sequence'].next_by_code('custom.payroll.slip')
                vals['name'] = sequence or 'New'
        return super().create(vals_list)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.version_id:
            self.total_gaji_pokok = self.employee_id.version_id.contract_wage

    def _auto_populate_basic_salary_and_bpjs(
        self, auto_create_basic=True, auto_populate_bpjs=True
    ):
        self.ensure_one()
        Detail = self.env['custom.payroll.slip.detail']
        existing_basic = self.detail_ids.filtered(lambda d: d.component_type == 'gaji_pokok')
        if auto_create_basic and not existing_basic and self.total_gaji_pokok:
            Detail.create({
                'slip_gaji_id': self.id,
                'component_type': 'gaji_pokok',
                'nominal': self.total_gaji_pokok,
                'description': 'Basic Salary',
            })
        if auto_populate_bpjs:
            existing_bpjs_ids = set(self.detail_ids.filtered(
                lambda d: d.component_type == 'bpjs'
            ).mapped('bpjs_id').ids)
            bpjs_records = self.env['custom.payroll.bpjs'].search([
                ('company_id', '=', self.company_id.id),
                ('status_aktif', '=', True),
            ])
            for bpjs in bpjs_records:
                if bpjs.id in existing_bpjs_ids:
                    continue
                if bpjs.persen:
                    nominal = bpjs.persen * self.total_gaji_pokok / 100.0
                else:
                    nominal = bpjs.nominal
                Detail.create({
                    'slip_gaji_id': self.id,
                    'component_type': 'bpjs',
                    'bpjs_id': bpjs.id,
                    'nominal': nominal,
                    'description': bpjs.name,
                })
        existing_potongan_master_ids = set(
            self.detail_ids.filtered(
                lambda d: d.component_type == 'potongan' and d.potongan_tetap_id
            ).mapped('potongan_tetap_id').ids
        )
        if self.employee_id and self.payroll_batch_id.periode_bulan and self.payroll_batch_id.periode_tahun:
            year = self.payroll_batch_id.periode_tahun
            month = int(self.payroll_batch_id.periode_bulan)
            try:
                period_start = date(year, month, 1)
                _, last_day = calendar.monthrange(year, month)
                period_end = date(year, month, last_day)
            except (ValueError, TypeError):
                period_start = period_end = False
            if period_start and period_end:
                potongan_records = self.env['custom.payroll.potongan.tetap'].search([
                    ('employee_id', '=', self.employee_id.id),
                    ('company_id', '=', self.company_id.id),
                    ('active', '=', True),
                    ('start_date', '<=', period_end),
                    '|',
                    ('end_date', '=', False),
                    ('end_date', '>=', period_start),
                ])
                for pot in potongan_records:
                    if pot.id in existing_potongan_master_ids:
                        continue
                    Detail.create({
                        'slip_gaji_id': self.id,
                        'component_type': 'potongan',
                        'potongan_tetap_id': pot.id,
                        'nominal': pot.amount,
                        'description': pot.name,
                    })
        existing_lembur = self.detail_ids.filtered(
            lambda d: d.component_type == 'lembur' and d.description == 'Auto Overtime'
        )
        if not existing_lembur and self.overtime_amount > 0:
            Detail.create({
                'slip_gaji_id': self.id,
                'component_type': 'lembur',
                'nominal': self.overtime_amount,
                'description': 'Auto Overtime',
            })
        self.with_context(payroll_internal_recompute=True).action_recompute_rules()

    def action_recompute_rules(self):
        self.ensure_one()
        if not self.env.context.get('payroll_internal_recompute'):
            self._check_payroll_manager()
        Detail = self.env['custom.payroll.slip.detail']
        self.detail_ids.filtered(lambda d: d.component_type == 'rule').unlink()
        engine = self.env['custom.payroll.rule.engine']
        for rule, amount in engine.run_rules(self):
            if not rule.appears_on_payslip or amount == 0.0:
                continue
            Detail.create({
                'slip_gaji_id': self.id,
                'component_type': 'rule',
                'rule_id': rule.id,
                'nominal': amount,
                'description': '[{}] {}'.format(rule.code, rule.name),
            })

    def action_confirm(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status == 'draft':
                rec.status = 'confirmed'

    def action_paid(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status == 'confirmed':
                rec.status = 'paid'

    def action_cancel(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status in ('draft', 'confirmed'):
                rec.status = 'cancelled'

    def _send_email(self, resend=False):
        self.ensure_one()
        if self.status != 'paid':
            return 'not_paid'
        if self.email_status == 'sent' and not resend:
            return 'already_sent'
        if not self.employee_id.work_email:
            self.write({
                'email_status': 'skipped',
                'email_sent_at': False,
                'email_sent_by': False,
                'email_error': 'Skipped because the employee has no work email address.',
            })
            return 'skipped'

        template = self.env.ref('hr_payroll_custom.mail_template_payroll_slip')
        try:
            mail_id = template.send_mail(
                self.id,
                force_send=True,
                raise_exception=True,
                email_layout_xmlid='mail.mail_notification_light',
            )

            mail = self.env['mail.mail'].sudo().browse(mail_id)
            if not mail.exists() or mail.state != 'sent':
                error = mail.failure_reason if mail.exists() else 'Email record was not created.'
                self.write({
                    'email_status': 'failed',
                    'email_mail_id': mail.id if mail.exists() else False,
                    'email_error': error or 'Email was not accepted by the outgoing mail server.',
                })
                return 'failed'
        except Exception as error:
            self.write({
                'email_status': 'failed',
                'email_error': str(error),
            })
            return 'failed'

        self.write({
            'email_status': 'sent',
            'email_sent_at': fields.Datetime.now(),
            'email_sent_by': self.env.user.id,
            'email_error': False,
            'email_mail_id': mail.id,
        })
        self.message_post(
            body=_('Payslip emailed successfully to %s.') % self.employee_id.work_email,
            subtype_xmlid='mail.mt_note',
        )
        return 'sent'

    def action_send_email(self):
        self._check_payroll_officer()
        results = {
            'sent': 0,
            'skipped': 0,
            'not_paid': 0,
            'already_sent': 0,
            'failed': 0,
        }
        for slip in self:
            results[slip._send_email()] += 1
        if len(self) == 1:
            result = next(key for key, value in results.items() if value)
            if result == 'not_paid':
                raise UserError(_('Only payslips with Paid status can be emailed.'))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payslip Email'),
                'message': _(
                    'Sent: %(sent)d, skipped (no email): %(skipped)d, '
                    'not paid: %(not_paid)d, already sent: %(already_sent)d, failed: %(failed)d.'
                ) % results,
                'type': 'warning' if any(results[key] for key in ('failed', 'skipped', 'not_paid')) else 'success',
                'sticky': bool(results['failed']),
            },
        }

    def action_resend_email(self):
        self._check_payroll_officer()
        results = {'sent': 0, 'skipped': 0, 'not_paid': 0, 'failed': 0}
        for slip in self:
            result = slip._send_email(resend=True)
            if result in results:
                results[result] += 1
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Payslip Email'),
                'message': _(
                    'Resent: %(sent)d, skipped (no email): %(skipped)d, '
                    'not paid: %(not_paid)d, failed: %(failed)d.'
                ) % results,
                'type': 'warning' if any(results[key] for key in ('failed', 'skipped', 'not_paid')) else 'success',
                'sticky': bool(results['failed']),
            },
        }

    def action_draft(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status == 'cancelled':
                rec.status = 'draft'

    def action_view_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Slip Details',
            'res_model': 'custom.payroll.slip.detail',
            'view_mode': 'list,form',
            'domain': [('slip_gaji_id', '=', self.id)],
            'context': {'default_slip_gaji_id': self.id},
        }
