from odoo import api, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    _ACCRUAL_FIELDS = {'contract_date_start', 'wage', 'date_version', 'active'}

    def write(self, vals):
        # Auto-sync date_version when contract_date_start changes
        # (Odoo 19 only does this for single-version employees)
        if vals.get('contract_date_start') and 'date_version' not in vals \
                and not self.env.context.get('sync_contract_dates'):
            vals = {**vals, 'date_version': vals['contract_date_start']}

        res = super().write(vals)
        if self._ACCRUAL_FIELDS & set(vals):
            emp_ids = self.mapped('employee_id').ids
            self.env['ksw.annual.leave']._refresh_accrual_for_employees(emp_ids)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        emp_ids = records.mapped('employee_id').ids
        self.env['ksw.annual.leave']._refresh_accrual_for_employees(emp_ids)
        return records
