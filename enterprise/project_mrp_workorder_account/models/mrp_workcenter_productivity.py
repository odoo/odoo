# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    def _create_analytic_entry(self, previous_duration=0, old_dist=None):
        """
            Used for updating or creating the employee analytic lines in 2 cases:
                - Update of the productivity for an employee, in which case old_dist is unused
                - Update of the project's MO, in which case previous_duration is unused
        """
        self.ensure_one()
        # TODO in master: Remove me and add prev_emp as a method parameter
        prev_emp = self.env.context.get('employee_change_id')
        employee_aal = self.workorder_id.employee_analytic_account_line_ids.sudo().filtered(
            lambda line: line.employee_id and (line.employee_id == self.employee_id or line.employee_id.id == prev_emp)
        )
        distribution_update = old_dist and employee_aal
        if distribution_update:
            old_dist = {k.split(',')[0]: old_dist[k] for k in old_dist}
            account = self.env['account.analytic.account'].browse(int(max(old_dist, key=old_dist.get)))
            biggest_aal = employee_aal.filtered(lambda line: line[account.plan_id._column_name()] == account)
            amount = biggest_aal.amount / (old_dist[str(account.id)] / 100)
            duration = biggest_aal.unit_amount
        else:
            duration = (self.duration - round(previous_duration, 2)) / 60.0

            amount = - duration * self.employee_cost

        line_vals = self.env['account.analytic.account']._perform_analytic_distribution(
            self.workorder_id.production_id.project_id.sudo()._get_analytic_distribution(), amount, duration, employee_aal, self, not (distribution_update or prev_emp))

        if prev_emp:
            employee_aal.employee_id = self.employee_id

        if line_vals:
            self.workorder_id.employee_analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(line_vals)

    def unlink(self):
        for time in self:
            # set previous_duration to 2 * time.duration to effectively
            # create an analytic entry for a length of -time.duration
            time._create_analytic_entry(2 * time.duration)
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        work_center_productivities = super().create(vals_list)
        for work_order, productivities in work_center_productivities.grouped('workorder_id').items():
            if (
                work_order.production_id.project_id.sudo()._get_analytic_distribution()
                or work_order.employee_analytic_account_line_ids
            ):
                for productivity in productivities:
                    productivity._create_analytic_entry()
        return work_center_productivities

    def write(self, vals):
        previous_state = {
            productivity: {'duration': productivity.duration, 'employee_id': productivity.employee_id.id}
            for productivity in self
        }

        res = super().write(vals)
        # if a value triggers a change of duration or employee we adapt the aals
        if {'date_start', 'date_end', 'employee_id'} & vals.keys():
            for work_order, productivities in self.grouped('workorder_id').items():
                if (
                        work_order.production_id.project_id.sudo()._get_analytic_distribution()
                        or work_order.employee_analytic_account_line_ids
                ):
                    for productivity in productivities:
                        prev_duration = previous_state[productivity]['duration'] if {'date_start', 'date_end'} & vals.keys() else 0
                        prev_employee = previous_state[productivity]['employee_id'] if 'employee_id' in vals else None
                        productivity.with_context(employee_change_id=prev_employee)._create_analytic_entry(prev_duration)
        return res
