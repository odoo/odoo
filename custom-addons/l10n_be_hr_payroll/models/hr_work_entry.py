#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    def init(self):
        # speeds up `l10n_be.work.entry.daily.benefit.report`
        self.env.cr.execute("""
            CREATE INDEX IF NOT EXISTS hr_work_entry_daily_benefit_idx
                ON hr_work_entry (active, employee_id)
                WHERE state IN ('draft', 'validated');
        """)
        super().init()

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        partial_sick_work_entry_type = self.env.ref('l10n_be_hr_payroll.work_entry_type_part_sick')
        leaves = self.env['hr.leave']
        for work_entry in res:
            if work_entry.work_entry_type_id == partial_sick_work_entry_type and work_entry.leave_id:
                leaves |= work_entry.leave_id
        activity_type_id = self.env.ref('mail.mail_activity_data_todo').id
        res_model_id = self.env.ref('hr_holidays.model_hr_leave').id
        for leave in leaves.sudo():
            user_ids = leave.holiday_status_id.responsible_ids.ids or self.env.user.ids
            note = _("Sick time off to report to DRS for %s.", leave.date_from.strftime('%B %Y'))
            activity_vals = []
            for user_id in user_ids:
                activity_vals.append({
                    'activity_type_id': activity_type_id,
                    'automated': True,
                    'note': note,
                    'user_id': user_id,
                    'res_id': leave.id,
                    'res_model_id': res_model_id,
                })
            self.env['mail.activity'].create(activity_vals)
        return res
