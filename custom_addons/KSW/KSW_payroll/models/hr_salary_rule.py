from odoo import api, models


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    @api.model
    def _ksw_sync_legacy_absence_deduction_rule(self):
        """Normalize legacy absence-deduction salary rules so they work with
        the current KSW worked-day codes.

        Two rules are patched:
        - ABSENCE_DED: old rule attached to legacy structures; used to read
          TOTDAYS which no longer exists.
        - MISDAYS (salary rule): legacy "Missed days(ATT SHEET)" rule that
          read worked_days.WORK100.number_of_days — WORK100 no longer exists
          so the attribute access on the float 0.0 crashes.

        Both are rewritten to read the monetary total from the MISDAYS
        worked-day line (populated by KSW as a backward-compatibility alias
        for ATT_DED).
        """
        _new_condition = "result = bool(worked_days.MISDAYS)"
        _new_amount = "result = -worked_days.MISDAYS.amount if worked_days.MISDAYS else 0.0"

        for code in ('ABSENCE_DED', 'MISDAYS'):
            rule = self.sudo().search([('code', '=', code)], limit=1)
            if not rule:
                continue
            rule.write({
                'condition_select': 'python',
                'condition_python': _new_condition,
                'amount_select': 'code',
                'amount_python_compute': _new_amount,
            })
        return True



