from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class CustomPayrollBatch(models.Model):
    _name = 'custom.payroll.batch'
    _description = 'Payroll Batch'
    _order = 'periode_tahun desc, periode_bulan desc'

    name = fields.Char(string='Name', compute='_compute_name', store=True)
    periode_bulan = fields.Selection(
        selection=[
            ('1', 'January'),
            ('2', 'February'),
            ('3', 'March'),
            ('4', 'April'),
            ('5', 'May'),
            ('6', 'June'),
            ('7', 'July'),
            ('8', 'August'),
            ('9', 'September'),
            ('10', 'October'),
            ('11', 'November'),
            ('12', 'December'),
        ],
        string='Period Month',
        required=True,
    )
    periode_tahun = fields.Integer(string='Period Year', required=True, default=lambda self: fields.Date.today().year)
    status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='draft',
        required=True,
    )
    slip_ids = fields.One2many('custom.payroll.slip', 'payroll_batch_id', string='Payslips')
    slip_count = fields.Integer(string='Slip Count', compute='_compute_slip_count')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True)

    submitter_id = fields.Many2one(
        'res.users',
        string='Submitter',
        readonly=True,
        default=lambda self: self.env.user,
    )
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        readonly=True,
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        readonly=True,
    )
    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        help='Reason provided when the last submission was rejected.',
    )

    def _check_payroll_officer(self):
        if not self.env.user.has_group('hr_payroll_custom.group_payroll_user'):
            raise AccessError(_('Only Payroll Officers or Administrators can manage payroll batches.'))

    def _check_payroll_manager(self):
        if not self.env.user.has_group('hr_payroll_custom.group_payroll_manager'):
            raise AccessError(_('Only Payroll Administrators can perform this action.'))

    @api.depends('periode_bulan', 'periode_tahun')
    def _compute_name(self):
        bulan_name = dict(self._fields['periode_bulan'].selection)
        for rec in self:
            if rec.periode_bulan and rec.periode_tahun:
                rec.name = f"Payroll {bulan_name.get(rec.periode_bulan, '')} {rec.periode_tahun}"
            else:
                rec.name = ''

    def _compute_slip_count(self):
        for rec in self:
            rec.slip_count = len(rec.slip_ids)

    def action_submit_for_approval(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status == 'draft':
                rec.status = 'submitted'
                rec.submitter_id = self.env.user
                rec.rejection_reason = False

    def action_approve(self):
        self._check_payroll_manager()
        for rec in self:
            if rec.status == 'submitted':
                rec.status = 'approved'
                rec.approver_id = self.env.user
                rec.approval_date = fields.Datetime.now()
                rec.rejection_reason = False

    def action_reject(self, reason):
        self._check_payroll_manager()
        for rec in self:
            if rec.status == 'submitted':
                rec.status = 'draft'
                rec.rejection_reason = reason or False
                rec.approver_id = False
                rec.approval_date = False

    def action_open_reject_wizard(self):
        self._check_payroll_manager()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Batch'),
            'res_model': 'custom.payroll.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
            },
        }

    def action_done(self):
        self._check_payroll_manager()
        for rec in self:
            if rec.status != 'approved':
                continue
            unpaid_slips = rec.slip_ids.filtered(lambda s: s.status not in ('paid', 'cancelled'))
            if unpaid_slips:
                raise UserError(_(
                    "Cannot mark batch '%(batch)s' as Done.\n"
                    "%(count)d payslip(s) are still not paid (must be 'paid' or 'cancelled')."
                ) % {'batch': rec.name, 'count': len(unpaid_slips)})
            rec.status = 'done'

    def action_cancel(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status in ('draft', 'submitted', 'approved'):
                rec.status = 'cancelled'

    def action_draft(self):
        self._check_payroll_officer()
        for rec in self:
            if rec.status == 'cancelled':
                rec.status = 'draft'

    def action_generate_payslips(self):
        self._check_payroll_officer()
        self.ensure_one()
        if self.status != 'draft':
            raise UserError(_("Payslips can only be generated while batch is in 'Draft' status."))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Generate Payslips'),
            'res_model': 'custom.payroll.generate.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_payroll_batch_id': self.id,
                'default_company_id': self.company_id.id,
            },
        }

    def action_view_slips(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payslips',
            'res_model': 'custom.payroll.slip',
            'view_mode': 'list,form',
            'domain': [('payroll_batch_id', '=', self.id)],
            'context': {'default_payroll_batch_id': self.id},
        }
