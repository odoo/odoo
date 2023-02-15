# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPlanEmployeeActivity(models.Model):
    _name = 'hr.plan.employee.activity'
    _description = 'Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    department_id = fields.Many2one(related='employee_id.department_id')
    image_128 = fields.Image(related='employee_id.image_128')
    company_id = fields.Many2one(related='employee_id.company_id')
    user_id = fields.Many2one(related='employee_id.user_id')
    summary = fields.Html(compute='_compute_summary')

    @api.depends('activity_ids.summary')
    def _compute_summary(self):
        for plan in self:
            plan.summary = self.env['ir.ui.view']._render_template('hr.hr_employee_plan_activity_summary', {
                'activity_ids': plan.activity_ids,
            })

    @api.autovacuum
    def _gc_employee_plan_activity(self):
        no_activities = self.env['hr.plan.employee.activity'].search(
            [('activity_ids', '=', False)]
        )
        no_activities.unlink()
