# -*- coding: utf-8 -*-
from odoo import _, models, fields


class MrpWorkcenterProductivity(models.Model):
    _inherit = "mrp.workcenter.productivity"

    def _compute_duration(self):
        previous_durations = self.mapped('duration')
        super()._compute_duration()
        for timer, previous_duration in zip(self, previous_durations):
            if timer.workorder_id.production_id.analytic_distribution or timer.workorder_id.employee_analytic_account_line_ids:
                timer._create_analytic_entry(previous_duration)

    def _prepare_analytic_line_values(self, account, amount, unit_amount):
        self.ensure_one()
        res = self.workorder_id._prepare_analytic_line_values(account, amount, unit_amount)
        res['name'] = _("[EMPL] %s - %s", self.workorder_id.display_name, self.employee_id.name)
        res['employee_id'] = self.employee_id.id
        return res

    def _create_analytic_entry(self, previous_duration=0, old_dist=None):
        """
            Used for updating or creating the employee analytic lines in 2 cases:
                - Update of the productivity for an employee, in which case old_dist is unused
                - Update of the MO analytic distribution, in which case previous_duration is unused
        """
        self.ensure_one()
        employee_aal = self.workorder_id.employee_analytic_account_line_ids.filtered(
            lambda line: line.employee_id and line.employee_id == self.employee_id
        )
        distribution_update = old_dist and employee_aal
        if distribution_update:
            account = self.env['account.analytic.account'].browse(int(max(old_dist, key=old_dist.get)))
            biggest_aal = employee_aal.filtered(lambda line: line[account.plan_id._column_name()] == account)
            amount = biggest_aal.amount / (old_dist[str(account.id)] / 100)
            duration = biggest_aal.unit_amount
        else:
            duration = (self.duration - previous_duration) / 60.0
            amount = - duration * self.employee_cost

        line_vals = self.env['account.analytic.account']._perform_analytic_distribution(
            self.workorder_id.production_id.analytic_distribution, amount, duration, employee_aal, self, not distribution_update)
        if line_vals:
            self.workorder_id.employee_analytic_account_line_ids += self.env['account.analytic.line'].sudo().create(line_vals)

    def unlink(self):
        for time in self:
            # set previous_duration to 2 * time.duration to effectively
            # create an analytic entry for a length of -time.duration
            time._create_analytic_entry(2 * time.duration)
        return super().unlink()

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    employee_analytic_account_line_ids = fields.Many2many('account.analytic.line', copy=False)

    def _compute_duration(self):
        self._create_or_update_analytic_entry()
        super()._compute_duration()

    def action_cancel(self):
        self.employee_analytic_account_line_ids.unlink()
        return super().action_cancel()

    def _update_productivity_analytic(self, old_dist):
        for time_id in self.time_ids:
            time_id._create_analytic_entry(previous_duration=0, old_dist=old_dist)
