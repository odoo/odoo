from dateutil.relativedelta import relativedelta
from itertools import groupby
from odoo import api, fields, models
from odoo.osv import expression


class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)
        contracts.filtered(lambda c: c.state in ('open', 'close'))._update_timesheets_for_public_holidays()
        return contracts

    def write(self, vals):
        res = super().write(vals)

        vals_list = ['date_start', 'date_end']
        if any(field in vals for field in vals_list):
            employees = self.mapped('employee_id')

            # we are calling the _get_public_holidays to get the public holidays
            # and if we dont have a date_end, we will take one year interval from today
            date_start = self.date_start
            date_end = self.date_end if self.date_end else fields.Date.today() + relativedelta(years=1)

            future_leaves = employees._get_public_holidays(date_start, date_end)
            if future_leaves:
                future_leaves._generate_public_time_off_timesheets(employees)
            self._update_timesheets_for_public_holidays()

        if vals.get('state') in ('open', 'close'):
            self._update_timesheets_for_public_holidays()

        return res

    def _update_timesheets_for_public_holidays(self):
        """ Removes timesheet entries linked to public holidays if they fall outside
            an employee's contract period """

        employees = self.mapped('employee_id')
        if not employees:
            return

        all_contracts_data = self.env['hr.contract'].sudo().search_read(
            [('employee_id', 'in', employees.ids),
            ('state', 'in', ['open', 'close'])],
            ['employee_id', 'date_start', 'date_end']
        )

        if not all_contracts_data:
            return

        employee_intervals = {}
        for emp_id, contracts in groupby(all_contracts_data, key=lambda c: c['employee_id'][0]):
            intervals = [
                (contract['date_start'], contract['date_end'] or None)
                for contract in contracts
            ]
            employee_intervals[emp_id] = intervals

        timesheets_to_remove = self.env['account.analytic.line']
        for emp in employees:
            domain = expression.AND([
                        [('employee_id', '=', emp.id)],
                        [('global_leave_id', '!=', False)],
                        expression.AND([
                            expression.OR([
                                [('date', '<', start)],
                                [('date', '>', end)]
                            ]) for start, end in employee_intervals[emp.id]
                        ])
                    ])
            timesheets_to_remove |= timesheets_to_remove.sudo().search(domain)

        if timesheets_to_remove:
            timesheets_to_remove.write({'global_leave_id': False})
            timesheets_to_remove.unlink()
