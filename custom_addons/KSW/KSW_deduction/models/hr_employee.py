from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_deduction_count = fields.Integer(
        string='Active Deductions',
        compute='_compute_deduction_count',
        groups='hr.group_hr_user',
    )
    x_deduction_monthly_total = fields.Monetary(
        string='Monthly Deduction Total',
        compute='_compute_deduction_count',
        groups='hr.group_hr_user',
        currency_field='x_deduction_currency_id',
    )
    x_deduction_currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_deduction_count',
        groups='hr.group_hr_user',
    )

    def _compute_deduction_count(self):
        company_currency = self.env.company.currency_id
        today = fields.Date.context_today(self)
        period_start = today.replace(day=1)
        for emp in self:
            active = self.env['ksw.deduction'].sudo().search([
                ('employee_id', '=', emp.id),
                ('state', '=', 'active'),
            ])
            emp.x_deduction_count = len(active)
            # Sum pending installments whose period is the current month
            monthly = 0.0
            for ded in active:
                for line in ded.line_ids:
                    if (line.state == 'pending'
                            and line.period_date
                            and line.period_date.year == period_start.year
                            and line.period_date.month == period_start.month):
                        monthly += line.amount
            emp.x_deduction_monthly_total = monthly
            emp.x_deduction_currency_id = company_currency

    def action_view_deductions(self):
        self.ensure_one()
        return {
            'name': 'Deductions of %s' % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ksw.deduction',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

