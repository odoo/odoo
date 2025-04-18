# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain


class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    department_id = fields.Many2one('hr.department', compute='_compute_department_id')
    plan_department_filterable = fields.Boolean(compute='_compute_plan_department_filterable')

    @api.depends('department_id')
    def _compute_plan_available_ids(self):
        todo = self.filtered(lambda s: s.plan_department_filterable)
        for scheduler in todo:
            domain = scheduler._get_plan_available_base_domain()
            if not scheduler.department_id:
                domain &= Domain('department_id', '=', False)
            else:
                domain &= Domain('department_id', '=', False) | Domain('department_id', '=', scheduler.department_id.id)
            scheduler.plan_available_ids = self.env['mail.activity.plan'].search(domain)
        super(MailActivitySchedule, self - todo)._compute_plan_available_ids()

    @api.depends('res_model')
    def _compute_plan_department_filterable(self):
        for wizard in self:
            wizard.plan_department_filterable = wizard.res_model == 'hr.employee'

    @api.depends('res_model_id', 'res_ids')
    def _compute_department_id(self):
        for wizard in self:
            if wizard.plan_department_filterable:
                applied_on = wizard._get_applied_on_records()
                all_departments = applied_on.department_id
                wizard.department_id = False if len(all_departments) > 1 else all_departments
            else:
                wizard.department_id = False

    def _compute_plan_date(self):
        todo = self.filtered(lambda s: s.res_model == 'hr.employee')
        for scheduler in todo:
            selected_employees = scheduler._get_applied_on_records()
            start_dates = selected_employees.filtered('date_start').mapped('date_start')
            if start_dates:
                today = fields.Date.today()
                planned_due_date = min(start_dates)
                if planned_due_date < today or (planned_due_date - today).days < 30:
                    scheduler.plan_date = today + relativedelta(days=+30)
                else:
                    scheduler.plan_date = planned_due_date
        super(MailActivitySchedule, self - todo)._compute_plan_date()
