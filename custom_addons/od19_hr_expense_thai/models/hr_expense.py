# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = 'hr.expense'

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
    ], string='Reimbursement Method', default='cash', tracking=True)
    reimbursement_date = fields.Date(
        string='Reimbursement Date',
        help='Date when the employee was reimbursed.',
    )
    first_approval_date = fields.Date(
        string='First Approval Date', readonly=True,
    )
    second_approver_id = fields.Many2one(
        'hr.employee', string='Second Approver',
        tracking=True,
    )
    second_approval_date = fields.Date(
        string='Second Approval Date', readonly=True,
    )
    thai_expense_type = fields.Selection([
        ('travel', 'Travel'),
        ('meal', 'Meal'),
        ('transport', 'Transportation'),
        ('accommodation', 'Accommodation'),
        ('communication', 'Communication'),
        ('office_supplies', 'Office Supplies'),
        ('medical', 'Medical'),
        ('training', 'Training'),
        ('other', 'Other'),
    ], string='Expense Type', default='other', tracking=True)
    require_second_approval = fields.Boolean(
        string='Require Second Approval',
        compute='_compute_require_second_approval', store=True,
    )
    second_approval_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
    ], string='Second Approval State', default='not_required', readonly=True, copy=False)
    od19_reimbursement_payment_id = fields.Many2one(
        'account.payment',
        string='Reimbursement Payment / รายการจ่ายคืนพนักงาน',
        readonly=True,
        copy=False,
        help='รายการจ่ายที่สร้างขึ้นเมื่อจ่ายคืนพนักงาน (Reconcile กับเจ้าหนี้พนักงาน)',
    )

    @api.depends('total_amount')
    def _compute_require_second_approval(self):
        """Require second approval for expenses above a threshold."""
        threshold = self.env['ir.config_parameter'].sudo().get_param(
            'od19_hr_expense_thai.second_approval_threshold', '5000')
        try:
            threshold = float(threshold)
        except (ValueError, TypeError):
            threshold = 5000.0
        for expense in self:
            expense.require_second_approval = expense.total_amount > threshold

    def action_approve_first(self):
        """First level approval."""
        for expense in self:
            if expense.state not in ('submitted',):
                raise UserError(_('Only submitted expenses can be approved.'))
            approver = expense.first_approver_id
            if approver and approver.user_id and approver.user_id != self.env.user:
                raise UserError(_(
                    'Only the designated first approver (%s) can approve this '
                    'expense.'
                ) % approver.display_name)
            expense.first_approver_id = self.env.user.employee_id
            expense.first_approval_date = fields.Date.context_today(expense)
            if expense.require_second_approval:
                expense.second_approval_state = 'pending'
            else:
                expense.action_approve_second()

    def action_approve_second(self):
        """Second level approval."""
        for expense in self:
            if expense.second_approval_state == 'approved':
                raise UserError(_('This expense has already been approved.'))
            if (
                expense.first_approver_id
                and expense.first_approver_id.user_id == self.env.user
            ):
                raise UserError(_(
                    'The second approver must be different from the first '
                    'approver.'
                ))
            expense.second_approver_id = self.env.user.employee_id
            expense.second_approval_date = fields.Date.context_today(expense)
            expense.second_approval_state = 'approved'
            # Call standard approve
            expense.action_approve()

    def action_refuse_second(self):
        """Second level refusal."""
        for expense in self:
            expense.second_approval_state = 'refused'
            expense.action_refuse()

    def action_mark_reimbursed(self):
        """Reimburse an employee-paid expense with a real payment.

        The old implementation only stamped a date, which left the employee
        payable open forever. A real outbound ``account.payment`` is now
        created, posted and reconciled against the payable line of the
        expense journal entry so the balance is really cleared.
        """
        for expense in self:
            if expense.payment_mode != 'own_account':
                raise UserError(_(
                    'Only expenses paid by employee can be reimbursed.'
                ))
            if expense.od19_reimbursement_payment_id:
                raise UserError(_(
                    'This expense was already reimbursed by the payment %s.'
                ) % expense.od19_reimbursement_payment_id.display_name)
            expense._od19_create_reimbursement_payment()
        return True

    def _od19_get_reimbursement_journal(self):
        """Return the bank/cash journal used to pay the employee back."""
        self.ensure_one()
        Journal = self.env['account.journal'].with_company(self.company_id)
        domain = Journal._check_company_domain(self.company_id)
        journal_type = 'cash' if self.payment_method == 'cash' else 'bank'
        journal = Journal.search(
            domain + [('type', '=', journal_type)], limit=1)
        if not journal:
            journal = Journal.search(
                domain + [('type', 'in', ('bank', 'cash'))], limit=1)
        if not journal:
            raise UserError(_(
                'No bank or cash journal is configured to reimburse this '
                'expense. Please create one first.'
            ))
        return journal

    def _od19_get_reimbursement_payment_method_line(self, journal):
        """Return an outbound payment method line able to post a payment.

        The chosen line must carry an outstanding account, otherwise Odoo
        refuses to generate the payment journal entry. Journals created from
        a chart template already have it; for hand-made journals we link the
        company outstanding account on the fly.
        """
        self.ensure_one()
        lines = journal.outbound_payment_method_line_ids
        if not lines:
            raise UserError(_(
                'The journal %s has no outbound payment method configured.'
            ) % journal.display_name)
        method_line = lines.filtered('payment_account_id')[:1] or lines[:1]
        if not method_line.payment_account_id:
            outstanding = (
                self.env['account.chart.template']
                .with_company(self.company_id)
                .ref('account_journal_payment_credit_account_id',
                     raise_if_not_found=False)
                or self.company_id.transfer_account_id
            )
            if not outstanding:
                raise UserError(_(
                    'No outstanding payments account is configured for the '
                    'journal %s.'
                ) % journal.display_name)
            method_line.payment_account_id = outstanding
        return method_line

    def _od19_create_reimbursement_payment(self):
        """Create, post and reconcile the reimbursement payment."""
        self.ensure_one()
        move = self.account_move_id
        if not move or move.state != 'posted':
            raise UserError(_(
                'Please post the expense before reimbursing it.'
            ))
        employee = self.employee_id
        partner = (employee.work_contact_id or employee.user_id.partner_id)
        if not partner:
            raise UserError(_(
                'No contact is linked to the employee %s, please configure one.'
            ) % employee.name)
        partner = partner.with_company(self.company_id)
        payable = partner.property_account_payable_id
        if not payable:
            raise UserError(_(
                'No payable account is configured for the employee contact %s.'
            ) % partner.display_name)

        journal = self._od19_get_reimbursement_journal()
        method_line = self._od19_get_reimbursement_payment_method_line(journal)
        date = self.reimbursement_date or fields.Date.context_today(self)

        payment = self.env['account.payment'].create({
            'payment_type': 'outbound',
            'partner_type': 'supplier',
            'partner_id': partner.id,
            'amount': self.total_amount,
            'currency_id': self.company_currency_id.id,
            'date': date,
            'journal_id': journal.id,
            'payment_method_line_id': method_line.id,
            'destination_account_id': payable.id,
            'memo': self.name,
            'od19_is_expense_payment': True,
        })
        payment.action_post()

        # Match the payment counterpart line with the payable line booked by
        # the expense receipt so the employee payable is cleared.
        lines = (move.line_ids + payment.move_id.line_ids).filtered_domain([
            ('account_id', '=', payable.id),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
        ])
        self.env['account.move']._od19_reconcile_move_lines(lines)

        self.write({
            'reimbursement_date': date,
            'od19_reimbursement_payment_id': payment.id,
        })
        return payment
