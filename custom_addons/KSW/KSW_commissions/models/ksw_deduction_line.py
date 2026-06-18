"""Extension of ksw.deduction.line for the commission-shortfall flow.

Adds three fields used by KSW_commissions:

* ``x_original_amount`` — captured on auto-generation; audit trail of
  the originally-scheduled installment amount (kept for traceability
  even though the new "park-for-commission" flow no longer relies on
  it for the live loans figure).
* ``x_paid_via_commission_sheet_id`` — set on each pending installment
  when a commission sheet's ``done`` action consumes it. Lets the
  reset path unwind the offset cleanly.
* ``x_awaiting_commission`` — accountant-set Boolean on a PENDING line
  meaning "this slice of the month's installment is to be recouped
  from the employee's commission sheet, not from payroll". Payroll
  skips lines with this flag (see ``hr_payslip._inject_ksw_deduction_inputs``
  override). The matching commission sheet's ``Loans (auto)`` field
  reads exactly the sum of these lines for the (employee, year, month).

We also override ``_generate_installment_lines`` (on the parent
``ksw.deduction``) to populate ``x_original_amount`` at creation time.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KswDeductionLine(models.Model):
    _inherit = 'ksw.deduction.line'

    x_original_amount = fields.Monetary(
        string='Originally Scheduled Amount', readonly=True, copy=False,
        help='Audit-only: amount this installment was created with '
             '(auto-generated or manually entered). The "Awaiting '
             'Commission" flag is now the authoritative signal that '
             'a slice of this month is being routed to the commission '
             'sheet — this field is kept purely for traceability.',
    )
    x_paid_via_commission_sheet_id = fields.Many2one(
        'ksw.commission.sheet', readonly=True, copy=False,
        ondelete='restrict',
        string='Paid via Commission Sheet',
        help='Set when a KSW Commissions sheet finalised this '
             'installment as paid. Lets the sheet reset path unwind '
             'the offset.',
    )
    x_awaiting_commission = fields.Boolean(
        string='Awaiting Commission',
        default=False,
        copy=False,
        help='Tick on a PENDING installment line to mean: do not '
             'deduct this slice from payroll — recoup it from the '
             'employee\'s monthly commission sheet instead. The '
             'matching commission sheet automatically picks it up '
             'in its "Loans (auto)" total. Cleared automatically '
             'when the line is paid via a commission sheet.',
    )
    # Non-stored helper: the commission sheet that *would* settle this
    # awaiting-commission line (matched by employee + year + month).
    # Computed only when ``x_awaiting_commission`` is True and the
    # line is still pending — once finalise stamps
    # ``x_paid_via_commission_sheet_id``, that field is the
    # authoritative link instead.
    x_pending_commission_sheet_id = fields.Many2one(
        'ksw.commission.sheet',
        string='Pending Commission Sheet',
        compute='_compute_pending_commission_sheet', store=True,
        help='The (existing) commission sheet that will settle this '
             'parked installment when finalised. Empty if no sheet '
             'exists yet for that employee/month.',
    )

    @api.depends('x_awaiting_commission', 'state', 'employee_id',
                 'year', 'month')
    def _compute_pending_commission_sheet(self):
        Sheet = self.env['ksw.commission.sheet'].sudo()
        # Group lines by (employee_id, year, month) for batched search.
        by_key = {}
        for line in self:
            line.x_pending_commission_sheet_id = False
            if not (line.x_awaiting_commission and line.state == 'pending'
                    and line.employee_id and line.year and line.month):
                continue
            try:
                period = fields.Date.to_date(
                    '%04d-%02d-01' % (line.year, line.month))
            except ValueError:
                continue
            by_key.setdefault(
                (line.employee_id.id, period), self.browse()
            )
            by_key[(line.employee_id.id, period)] |= line
        if not by_key:
            return
        # One search per distinct (employee, period) — typically very
        # few keys per recordset render.
        for (emp_id, period), lines in by_key.items():
            sheet = Sheet.search([
                ('employee_id', '=', emp_id),
                ('period', '=', period),
            ], limit=1)
            for line in lines:
                line.x_pending_commission_sheet_id = sheet.id or False

    # ------------------------------------------------------------------
    # Settlement label override — show parked / commission-paid states.
    # ------------------------------------------------------------------
    @api.depends('x_awaiting_commission', 'x_paid_via_commission_sheet_id',
                 'x_paid_via_commission_sheet_id.name',
                 'x_pending_commission_sheet_id',
                 'x_pending_commission_sheet_id.name')
    def _compute_settlement_label(self):
        super()._compute_settlement_label()
        for line in self:
            # 1) Already finalised by a commission sheet — overrides
            #    every other label, including the parent's "Manual
            #    by ..." since x_paid_via_commission_sheet_id is the
            #    authoritative settlement.
            if line.x_paid_via_commission_sheet_id:
                line.settlement_label = _(
                    'Paid via Commission Sheet %s',
                    line.x_paid_via_commission_sheet_id.name or '',
                )
                continue
            # 2) Pending and parked for the commission — show the
            #    matching sheet ref if one exists, otherwise just
            #    flag it as awaiting.
            if line.x_awaiting_commission and line.state == 'pending':
                sheet = line.x_pending_commission_sheet_id
                if sheet:
                    line.settlement_label = _(
                        'Awaiting Commission Sheet %s', sheet.name or '',
                    )
                else:
                    line.settlement_label = _(
                        'Awaiting Commission Sheet (not yet created)',
                    )

    # ------------------------------------------------------------------
    # Create override — let the accountant add a PENDING
    # awaiting-commission sibling without the manual-paid forcing.
    # ------------------------------------------------------------------
    # The base ``KSW_deduction`` create override (in
    # ksw_deduction_line.py of that module) forces every non-auto
    # create to ``is_manual=True, state='paid'`` so it can only be
    # used for cash/bank manual entries. Adding a pending
    # awaiting-commission row needs a different path: still gated
    # behind ``group_installment_edit`` (just like manual entries),
    # but kept in ``state='pending'`` and ``is_manual=False`` so the
    # commission sheet can later flip it to paid.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        # Detect any vals that explicitly request the awaiting-commission
        # path. Auto-generation (parent ``_generate_installment_lines``)
        # never sets ``x_awaiting_commission``, so this branch only
        # fires for genuine accountant-driven creates.
        flagged = [v for v in vals_list if v.get('x_awaiting_commission')]
        if not flagged or self.env.context.get('_ksw_auto_generating'):
            return super().create(vals_list)
        # Process the two groups separately so each goes through the
        # right code path on the parent.
        normal_vals = [v for v in vals_list if not v.get('x_awaiting_commission')]
        results = self.env['ksw.deduction.line']
        if normal_vals:
            results |= super().create(normal_vals)
        # Awaiting-commission rows: gate the privilege ourselves and
        # forward to super with ``_ksw_auto_generating=True`` so the
        # parent skips its manual-create gate (which would force
        # ``is_manual=True, state='paid'``).
        if flagged and not self.env.su:
            user = self.env.user
            if not user.has_group('KSW_deduction.group_installment_edit'):
                raise UserError(_(
                    "Adding an 'Awaiting Commission' installment "
                    "requires the 'Loan Installment Modification' "
                    "privilege. Ask an administrator to grant it."
                ))
        for v in flagged:
            v.setdefault('state', 'pending')
            v.setdefault('is_manual', False)
            # Stamp x_original_amount on creation for parity with
            # auto-generated lines (audit trail).
            if 'x_original_amount' not in v:
                v['x_original_amount'] = v.get('amount', 0.0)
            if v.get('payslip_id'):
                raise UserError(_(
                    "An 'Awaiting Commission' installment cannot be "
                    "linked to a payslip — it represents a slice "
                    "routed to the commission sheet."
                ))
        results |= super(KswDeductionLine, self.with_context(
            _ksw_auto_generating=True,
        )).create(flagged)
        return results


