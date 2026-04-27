"""Extensions of ksw.deduction for the KSW_commissions awaiting-commission flow.
* Override ``_generate_installment_lines`` to stamp ``x_original_amount``
  on each newly-created line (audit trail).
* Add ``_get_pending_commission_lines_for_period`` helper used by the
  commission sheet to compute the auto-pulled "Loans" deductible.
"""
from odoo import api, fields, models


class KswDeduction(models.Model):
    _inherit = 'ksw.deduction'

    # ------------------------------------------------------------------
    # Stamp x_original_amount on newly-generated installment lines.
    # ------------------------------------------------------------------
    def _generate_installment_lines(self):
        before = set(self.line_ids.ids)
        super()._generate_installment_lines()
        new_lines = self.line_ids.filtered(lambda l: l.id not in before)
        for line in new_lines:
            # Bypass the line write override (which gates amount changes
            # behind group_installment_edit) — this is internal
            # scaffolding, not a user edit. We only set x_original_amount;
            # ``amount`` itself is untouched.
            line.sudo().write({'x_original_amount': line.amount})

    # ------------------------------------------------------------------
    # Helpers — used by ksw.commission.sheet
    # ------------------------------------------------------------------
    @staticmethod
    def _period_to_year_month(period_date):
        d = fields.Date.to_date(period_date)
        return d.year, d.month

    @api.model
    def _get_pending_commission_lines_for_period(self, employee, period_date):
        """Return ``(total, lines)`` for an employee's pending
        installments parked for commission settlement in the (year,
        month) of ``period_date``.

        ``total`` is the sum of every PENDING ``ksw.deduction.line.amount``
        with ``x_awaiting_commission=True`` that falls in the target
        month for the given employee, restricted to deductions in
        state ``'active'``.

        ``lines`` is the matching recordset, ordered FIFO across loans
        (oldest deduction first, then by sequence) — the commission
        sheet's ``done`` walker uses this order to decide which lines
        to pay through the commission first when the locked amount only
        covers part of the month's parked installments.
        """
        if not employee or not period_date:
            return 0.0, self.env['ksw.deduction.line']
        year, month = self._period_to_year_month(period_date)
        Line = self.env['ksw.deduction.line'].sudo()
        lines = Line.search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'pending'),
            ('year', '=', year),
            ('month', '=', month),
            ('x_awaiting_commission', '=', True),
            ('deduction_id.state', '=', 'active'),
        ]).sorted(key=lambda l: (
            l.deduction_id.create_date or fields.Datetime.now(),
            l.sequence, l.id,
        ))
        total = sum(lines.mapped('amount'))
        return total, lines
