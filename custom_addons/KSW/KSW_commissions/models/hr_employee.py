from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ``hr.employee`` custom fields that don't exist on hr.employee.public
    # MUST declare ``groups='hr.group_hr_user'`` (AGENTS.md gotcha) to
    # avoid AccessError on prefetch for non-HR users.
    x_site_id = fields.Many2one(
        'ksw.site', string='Work Site',
        groups='hr.group_hr_user',
        help='Site assignment used by the KSW driver-commission '
             'sub-form. Site change mid-month: the driver line is '
             'recorded on the month-end site only.',
    )
    x_commission_import_name = fields.Char(
        string='Commission Import Name',
        groups='hr.group_hr_user',
        help='Name exactly as it appears in the accountant\'s monthly '
             'Sales / Collection Excel files (column "البائع" / '
             '"مندوب التحصيل"). Used by the Excel import wizard to '
             'auto-match rows to this employee. Leave blank to fall back '
             'to the employee\'s regular name.',
    )

    # ------------------------------------------------------------------
    # Auto-create the current-month commission sheet when an HR officer
    # toggles ``x_is_attendance_sheet`` ON. Mirrors the pattern in
    # KSW_attendance_sheet but is **independent** — commission sheets
    # have their own draft/confirmed/done lifecycle separate from
    # attendance-sheet lifecycle.
    # ------------------------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if vals.get('x_is_attendance_sheet'):
            # Only employees that just transitioned to True need a sheet.
            self.env['ksw.commission.sheet']._ensure_current_period_sheets(
                self.filtered(lambda e: e.x_is_attendance_sheet))
        return res

