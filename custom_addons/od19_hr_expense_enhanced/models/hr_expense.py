# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    # ------------------------------------------------------------------
    # 1. Department head as auto approver
    # ------------------------------------------------------------------
    # The "First Approver" is the person expected to give the first level of
    # approval (by default the employee's department manager). This module
    # owns the field so the declaration and the auto-fill logic stay together;
    # ``od19_hr_expense_thai`` reuses it for the two-tier approval workflow.
    first_approver_id = fields.Many2one(
        'hr.employee',
        string='First Approver (Dept Head) / ผู้อนุมัติชั้นที่ 1',
        tracking=True,
        help="Employee expected to give the first approval. Auto-filled from "
             "the employee's department manager and editable afterwards.",
    )

    # ------------------------------------------------------------------
    # 5. Delegate approvals (on hr.expense since hr.expense.sheet was
    #    removed in Odoo 19)
    # ------------------------------------------------------------------
    od19_delegate_approver_id = fields.Many2one(
        'res.users',
        string='Delegate Approver / ผู้มอบหมายอนุมัติ',
        tracking=True,
        help='User to whom the approval has been delegated.',
    )
    od19_delegated_by_id = fields.Many2one(
        'res.users',
        string='Delegated By / ผู้มอบหมาย',
        readonly=True,
        tracking=True,
    )
    od19_delegation_date = fields.Datetime(
        string='Delegation Date / วันที่มอบหมาย',
        readonly=True,
    )

    # ------------------------------------------------------------------
    # 2. Cash tracking state
    # ------------------------------------------------------------------
    od19_cash_state = fields.Selection(
        [
            ('not_received', 'Not Received / ยังไม่ได้รับเงิน'),
            ('received', 'Received / ได้รับเงินแล้ว'),
            ('used', 'Used / ใช้เงินแล้ว'),
            ('returned', 'Returned / คืนเงินแล้ว'),
        ],
        string='Cash State / สถานะเงินสด',
        default='not_received',
        tracking=True,
        copy=False,
        help=(
            'Tracks the physical cash lifecycle of the expense: '
            'not received -> received -> used -> returned.'
        ),
    )

    # ------------------------------------------------------------------
    # Auto-approver logic
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('first_approver_id'):
                employee_id = vals.get('employee_id')
                if employee_id:
                    approver = self._get_department_head_approver(employee_id)
                    if approver:
                        vals['first_approver_id'] = approver.id
        return super().create(vals_list)

    def write(self, vals):
        if 'employee_id' in vals and 'first_approver_id' not in vals:
            employee_id = vals['employee_id']
            approver = self._get_department_head_approver(employee_id)
            if approver:
                vals['first_approver_id'] = approver.id
        return super().write(vals)

    @api.onchange('employee_id')
    def _onchange_employee_id_set_approver(self):
        if self.employee_id:
            approver = self._get_department_head_approver(self.employee_id.id)
            if approver:
                self.first_approver_id = approver

    @api.model
    def _get_department_head_approver(self, employee_id):
        """Return the department manager (hr.employee) of the given employee."""
        employee = self.env['hr.employee'].browse(employee_id)
        if not employee:
            return self.env['hr.employee']
        manager = employee.department_id.manager_id if employee.department_id else False
        return manager or self.env['hr.employee']

    # ------------------------------------------------------------------
    # Cash state actions
    # ------------------------------------------------------------------
    def action_receive_cash(self):
        """Mark cash as received."""
        for expense in self:
            if expense.od19_cash_state != 'not_received':
                raise UserError(_(
                    'Cash can only be received when state is "Not Received".'
                ))
            expense.od19_cash_state = 'received'
        return True

    def action_use_cash(self):
        """Mark cash as used."""
        for expense in self:
            if expense.od19_cash_state != 'received':
                raise UserError(_(
                    'Cash can only be used when state is "Received".'
                ))
            expense.od19_cash_state = 'used'
        return True

    def action_open_return_cash_wizard(self):
        """Open the return cash wizard."""
        self.ensure_one()
        if self.od19_cash_state not in ('received', 'used'):
            raise UserError(_(
                'Cash can only be returned when state is "Received" or "Used".'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Cash / คืนเงิน'),
            'res_model': 'od19.expense.return.cash',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_expense_id': self.id,
                'default_amount': self.total_amount,
            },
        }

    def action_open_reset_wizard(self):
        """Open the reset cash state wizard (admin only)."""
        self.ensure_one()
        if not self.env.is_admin():
            raise UserError(_(
                'Only administrators can reset the cash state.'
            ))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reset Cash State / รีเซ็ตสถานะเงินสด'),
            'res_model': 'od19.expense.reset',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_id': self.id},
        }

    # ------------------------------------------------------------------
    # XLSX export helper (tree view button)
    # ------------------------------------------------------------------
    def action_open_xlsx_export_wizard(self):
        """Open the XLSX export wizard from the expense tree view."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Export Expenses to XLSX / ส่งออกเป็น XLSX'),
            'res_model': 'od19.expense.xlsx.export',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_ids': self.ids or self.env.context.get('active_ids', [])},
        }

    # ------------------------------------------------------------------
    # Delegate approval actions
    # ------------------------------------------------------------------
    def action_delegate_approval(self):
        """Open the delegation wizard to transfer approval to another user."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delegate Approval / มอบหมายการอนุมัติ'),
            'res_model': 'od19.expense.delegate',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_expense_id': self.id},
        }

    def action_approve_delegate(self):
        """Delegate approver approves the expense."""
        self.ensure_one()
        if not self.od19_delegate_approver_id:
            raise UserError(_('No delegate approver has been assigned.'))
        if self.env.user != self.od19_delegate_approver_id:
            raise UserError(_(
                'Only the assigned delegate approver can perform this action.'
            ))
        self.action_approve()
        return True

    def action_refuse_delegate(self):
        """Delegate approver refuses the expense."""
        self.ensure_one()
        if not self.od19_delegate_approver_id:
            raise UserError(_('No delegate approver has been assigned.'))
        if self.env.user != self.od19_delegate_approver_id:
            raise UserError(_(
                'Only the assigned delegate approver can perform this action.'
            ))
        return self.action_refuse()

    def action_clear_delegate(self):
        """Clear the delegate approver."""
        self.ensure_one()
        self.od19_delegate_approver_id = False
        self.od19_delegated_by_id = False
        self.od19_delegation_date = False
        return True

    # ------------------------------------------------------------------
    # Supporting document type - payment certificate in lieu of receipt
    # (ใบรับรองแทนใบเสร็จรับเงิน)
    # ------------------------------------------------------------------
    # A payment certificate is used when the payee cannot issue a receipt
    # (e.g. a small cash purchase from a non-VAT-registered person). The
    # document carries no input VAT, so the whole amount is booked as an
    # expense and no input tax credit may be claimed.
    od19_document_type = fields.Selection(
        [
            ('tax_invoice', 'ใบกำกับภาษี / Tax Invoice'),
            ('receipt', 'ใบเสร็จรับเงิน / Receipt'),
            ('payment_certificate',
             'ใบรับรองแทนใบเสร็จรับเงิน / Payment Certificate'),
        ],
        string='ประเภทเอกสาร / Document Type',
        default='tax_invoice',
        required=True,
        tracking=True,
        help=(
            'Thai supporting-document type. Choose "ใบรับรองแทนใบเสร็จรับเงิน" '
            'when the payee cannot issue a receipt: the input VAT is then not '
            'claimable and the whole amount is booked as an expense.'
        ),
    )
    od19_certificate_number = fields.Char(
        string='เลขที่ใบรับรอง / Certificate No',
        copy=False,
        help='Running number printed on the payment certificate.',
    )
    od19_vat_creditable = fields.Boolean(
        string='ภาษีซื้อหักได้ / Input VAT Creditable',
        compute='_compute_od19_vat_creditable',
        store=True,
        help='Unticked for a payment certificate: the payee does not charge '
             'VAT, so no input tax can be claimed against output VAT.',
    )

    @api.depends('od19_document_type')
    def _compute_od19_vat_creditable(self):
        for expense in self:
            expense.od19_vat_creditable = (
                expense.od19_document_type != 'payment_certificate'
            )

    @api.depends('product_id', 'company_id', 'od19_document_type')
    def _compute_tax_ids(self):
        """Default taxes come from the product.

        A payment certificate in lieu of receipt
        (ใบรับรองแทนใบเสร็จรับเงิน) never carries VAT, so no input tax is
        applied even when the product has default purchase taxes.
        """
        for expense in self:
            if not expense.company_id:
                continue
            if expense.od19_document_type == 'payment_certificate':
                expense.tax_ids = False
            else:
                expense.tax_ids = (
                    expense.product_id.supplier_taxes_id.filtered_domain(
                        self.env['account.tax']._check_company_domain(
                            expense.company_id
                        )
                    )
                )

    @api.onchange('od19_document_type')
    def _onchange_od19_document_type(self):
        """A payment certificate never carries VAT, so drop any tax."""
        if self.od19_document_type == 'payment_certificate':
            self.tax_ids = [(5, 0, 0)]

    @api.constrains('od19_document_type', 'tax_ids')
    def _check_od19_payment_certificate_has_no_tax(self):
        for expense in self:
            if expense.od19_document_type == 'payment_certificate' and expense.tax_ids:
                raise ValidationError(_(
                    'A payment certificate in lieu of receipt '
                    '(ใบรับรองแทนใบเสร็จรับเงิน) cannot carry VAT. '
                    'Please remove the taxes or choose another document type.'
                ))

    # ------------------------------------------------------------------
    # Per diem allowance - Section 42(3) Revenue Code
    # (เบี้ยเลี้ยง ม.42(3))
    # ------------------------------------------------------------------
    # A travel per-diem allowance is exempt from personal income tax up to
    # the standard rate set by the company policy. When the claimed amount
    # exceeds that limit the employee must justify it for the approver.
    od19_is_per_diem = fields.Boolean(
        string='Per Diem Allowance / เบี้ยเลี้ยง',
        tracking=True,
        help='Tick when this expense is a travel per-diem allowance '
             'exempt under Section 42(3) of the Revenue Code.',
    )
    od19_per_diem_region = fields.Selection(
        [
            ('domestic', 'Domestic / ในประเทศ'),
            ('overseas', 'Overseas / ต่างประเทศ'),
        ],
        string='Region / พื้นที่',
        default='domestic',
        tracking=True,
    )
    od19_per_diem_days = fields.Float(
        string='Days / จำนวนวัน',
        default=1.0,
        tracking=True,
    )
    od19_per_diem_standard_rate = fields.Monetary(
        string='Standard Rate / Day / วงเงินมาตรฐานต่อวัน',
        compute='_compute_od19_per_diem', store=True,
        currency_field='currency_id',
        help='Standard exempt rate per day taken from the company policy.',
    )
    od19_per_diem_limit = fields.Monetary(
        string='Allowance Limit / วงเงินเบี้ยเลี้ยง',
        compute='_compute_od19_per_diem', store=True,
        currency_field='currency_id',
        help='Standard rate per day multiplied by the number of days.',
    )
    od19_per_diem_over_limit = fields.Boolean(
        string='Over Limit / เกินวงเงิน',
        compute='_compute_od19_per_diem', store=True,
        help='Set when the claimed allowance is above the standard limit.',
    )
    od19_per_diem_reason = fields.Text(
        string='Over-limit Reason / เหตุผลที่เกินวงเงิน',
        help='Required when the allowance exceeds the standard limit. '
             'The approver reviews this justification.',
    )

    @api.depends('od19_is_per_diem', 'od19_per_diem_region',
                 'od19_per_diem_days', 'total_amount', 'company_id')
    def _compute_od19_per_diem(self):
        for expense in self:
            if not expense.od19_is_per_diem or not expense.company_id:
                expense.od19_per_diem_standard_rate = 0.0
                expense.od19_per_diem_limit = 0.0
                expense.od19_per_diem_over_limit = False
                continue
            rate = expense.company_id._od19_per_diem_rate(
                expense.od19_per_diem_region)
            limit = rate * (expense.od19_per_diem_days or 0.0)
            expense.od19_per_diem_standard_rate = rate
            expense.od19_per_diem_limit = limit
            expense.od19_per_diem_over_limit = expense.total_amount > limit

    @api.constrains('od19_is_per_diem', 'od19_per_diem_over_limit',
                    'od19_per_diem_reason')
    def _check_od19_per_diem_over_limit_reason(self):
        for expense in self:
            if (expense.od19_is_per_diem
                    and expense.od19_per_diem_over_limit
                    and not (expense.od19_per_diem_reason or '').strip()):
                raise ValidationError(_(
                    'The per-diem allowance exceeds the standard limit. '
                    'Please provide a reason for the approver.'
                ))
