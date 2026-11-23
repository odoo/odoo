from odoo import api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        for payslip in self:
            self._inject_ksw_deduction_inputs(payslip)
        return super().compute_sheet()

    @api.model
    def get_inputs(self, versions, date_from, date_to):
        """Extend base payslip input generation so pending KSW deduction
        installments appear in "Other Inputs" immediately upon payslip
        creation (i.e. at `onchange_employee` time), not only after
        Compute. `compute_sheet` still deletes + regenerates KSW_DED_*
        inputs, so this is just for the create/onchange path.
        """
        res = super().get_inputs(versions, date_from, date_to)
        if not versions or not date_from or not date_to:
            return res
        employees = versions.mapped('employee_id')
        if not employees:
            return res
        lines = self.env['ksw.deduction.line'].sudo().search([
            ('employee_id', 'in', employees.ids),
            ('state', '=', 'pending'),
            ('period_date', '>=', date_from),
            ('period_date', '<=', date_to),
            ('deduction_id.state', '=', 'active'),
        ])
        if not lines:
            return res
        # Map employee -> version (pick first matching version per employee)
        emp_version = {}
        for v in versions:
            emp_version.setdefault(v.employee_id.id, v.id)
        for line in lines:
            version_id = emp_version.get(line.employee_id.id)
            if not version_id:
                continue
            ded = line.deduction_id
            res.append({
                'name': '%s [%s] inst %d/%d' % (
                    ded.type_id.name, ded.name,
                    line.sequence, ded.installments),
                'code': 'KSW_DED_%d' % line.id,
                'amount': line.amount,
                'version_id': version_id,
            })
        return res

    def _inject_ksw_deduction_inputs(self, payslip):
        if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
            return
        old = payslip.input_line_ids.filtered(
            lambda i: i.code and i.code.startswith('KSW_DED_'))
        if old:
            old.unlink()
        lines = self.env['ksw.deduction.line'].sudo().search([
            ('employee_id', '=', payslip.employee_id.id),
            ('state', '=', 'pending'),
            ('period_date', '>=', payslip.date_from),
            ('period_date', '<=', payslip.date_to),
            ('deduction_id.state', '=', 'active'),
        ])
        if not lines:
            return
        version_id = (
            payslip.version_id.id
            or (payslip.employee_id.current_version_id
                and payslip.employee_id.current_version_id.id)
        )
        if not version_id:
            return
        InputLine = self.env['hr.payslip.input'].sudo()
        seq = 50
        for line in lines:
            ded = line.deduction_id
            label = '%s [%s] inst %d/%d' % (
                ded.type_id.name, ded.name, line.sequence, ded.installments)
            InputLine.create({
                'payslip_id': payslip.id,
                'version_id': version_id,
                'name': label,
                'code': 'KSW_DED_%d' % line.id,
                'amount': line.amount,
                'sequence': seq,
            })
            seq += 1

    def write(self, vals):
        new_state = vals.get('state')
        prev = {s.id: s.state for s in self} if new_state else {}
        result = super().write(vals)
        if new_state:
            for slip in self:
                old = prev.get(slip.id)
                if new_state == 'done' and old != 'done':
                    self._sync_deductions_on_done(slip)
                elif new_state in ('draft', 'cancel') and old == 'done':
                    self._sync_deductions_on_reset(slip)
        return result

    def _sync_deductions_on_done(self, payslip):
        line_ids = [
            int(i.code[8:])
            for i in payslip.input_line_ids
            if i.code and i.code.startswith('KSW_DED_') and i.code[8:].isdigit()
        ]
        if not line_ids:
            return
        self.env['ksw.deduction'].sudo()._mark_lines_paid(line_ids, payslip)

    def _sync_deductions_on_reset(self, payslip):
        self.env['ksw.deduction'].sudo()._unmark_lines_paid(payslip)

