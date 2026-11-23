"""Override ``hr.payslip`` to keep KSW deduction lines flagged
``x_awaiting_commission`` out of the payroll input list.

Lines parked on a loan with ``x_awaiting_commission=True`` are by
definition routed to the employee's monthly KSW commission sheet
instead of payroll. Without this override they would be deducted
twice (once via salary, once via commission).

The override post-filters the parent's results rather than rerunning
the search from scratch — minimal behavioural change, no duplicated
SQL.
"""
from odoo import api, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.model
    def get_inputs(self, versions, date_from, date_to):
        res = super().get_inputs(versions, date_from, date_to)
        if not res:
            return res
        Line = self.env['ksw.deduction.line'].sudo()
        # Each KSW deduction input has code ``KSW_DED_<line_id>``.
        # Build a set of line ids flagged awaiting-commission so we
        # can drop them from the input list. Doing this in one
        # search avoids N round-trips when the payslip covers a
        # heavy month.
        candidate_ids = []
        for inp in res:
            code = inp.get('code') or ''
            if code.startswith('KSW_DED_') and code[8:].isdigit():
                candidate_ids.append(int(code[8:]))
        if not candidate_ids:
            return res
        parked_ids = set(Line.search([
            ('id', 'in', candidate_ids),
            ('x_awaiting_commission', '=', True),
        ]).ids)
        if not parked_ids:
            return res
        return [
            inp for inp in res
            if not (
                (inp.get('code') or '').startswith('KSW_DED_')
                and (inp['code'][8:].isdigit())
                and int(inp['code'][8:]) in parked_ids
            )
        ]

    def _inject_ksw_deduction_inputs(self, payslip):
        super()._inject_ksw_deduction_inputs(payslip)
        # Drop KSW_DED_* input lines whose underlying installment is
        # parked for commission settlement.
        ksw_inputs = payslip.input_line_ids.filtered(
            lambda i: i.code and i.code.startswith('KSW_DED_')
            and i.code[8:].isdigit()
        )
        if not ksw_inputs:
            return
        line_ids = [int(i.code[8:]) for i in ksw_inputs]
        parked_ids = set(self.env['ksw.deduction.line'].sudo().search([
            ('id', 'in', line_ids),
            ('x_awaiting_commission', '=', True),
        ]).ids)
        if not parked_ids:
            return
        to_drop = ksw_inputs.filtered(
            lambda i: int(i.code[8:]) in parked_ids)
        if to_drop:
            to_drop.sudo().unlink()

