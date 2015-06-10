# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil.relativedelta import relativedelta

from openerp import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    appraisal_date = fields.Date(string='Next Appraisal Date', help="The date of the next appraisal is computed by the appraisal plan's dates (first appraisal + periodicity).")
    appraisal_by_manager = fields.Boolean(string='Manager')
    appraisal_manager_ids = fields.Many2many('hr.employee', 'emp_appraisal_manager_rel', 'hr_appraisal_id')
    appraisal_manager_survey_id = fields.Many2one('survey.survey', string="Manager's Appraisal")
    appraisal_by_colleagues = fields.Boolean(string='Colleagues')
    appraisal_colleagues_ids = fields.Many2many('hr.employee', 'emp_appraisal_colleagues_rel', 'hr_appraisal_id')
    appraisal_colleagues_survey_id = fields.Many2one('survey.survey', string="Employee's Appraisal")
    appraisal_self = fields.Boolean(string='Employee')
    appraisal_employee = fields.Char(string='Employee Name')
    appraisal_self_survey_id = fields.Many2one('survey.survey', string='Self Appraisal')
    appraisal_by_collaborators = fields.Boolean(string='Collaborator')
    appraisal_by_collaborators_ids = fields.Many2many('hr.employee', 'emp_appraisal_subordinates_rel', 'hr_appraisal_id')
    appraisal_by_collaborators_survey_id = fields.Many2one('survey.survey', string="collaborate's Appraisal")
    periodic_appraisal = fields.Boolean(string='Periodic Appraisal', default=False)
    appraisal_repeat_number = fields.Integer(string='Repeat Every', default=1)
    appraisal_repeat_delay = fields.Selection([('year', 'Year'), ('month', 'Month')], string='Repeat Every', copy=False, default='year')
    appraisal_count = fields.Integer(compute='_compute_appraisal_count', string='Appraisals')
    related_partner_id = fields.Many2one('res.partner', compute='_compute_related_partner')

    @api.multi
    def _compute_appraisal_count(self):
        appraisal = self.env['hr.appraisal'].read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['employee_id'])
        result = dict((data['employee_id'][0], data['employee_id_count']) for data in appraisal)
        for employee in self:
            employee.appraisal_count = result.get(employee.id, 0)

    @api.one
    def _compute_related_partner(self):
        self.related_partner_id = self.user_id.partner_id or self.address_home_id

    @api.onchange('appraisal_by_manager', 'parent_id')
    def onchange_manager_appraisal(self):
        if self.appraisal_by_manager:
            self.appraisal_manager_ids = [self.parent_id.id]

    @api.onchange('appraisal_self')
    def onchange_self_employee(self):
        self.appraisal_employee = self.name

    @api.onchange('appraisal_by_colleagues')
    def onchange_colleagues(self):
        if self.department_id:
            self.appraisal_colleagues_ids = self.search([('department_id', '=', self.department_id.id), ('parent_id', '!=', False)])

    @api.onchange('appraisal_by_collaborators')
    def onchange_subordinates(self):
        self.appraisal_by_collaborators_ids = self.search([('parent_id', '!=', False)]).mapped('parent_id')

    @api.model
    def run_employee_appraisal(self, automatic=False, use_new_cursor=False):  # cronjob
        current_date = datetime.date.today()
        for employee in self.search([('appraisal_date', '<=', current_date)]):
            months = employee.appraisal_repeat_number if employee.appraisal_repeat_delay == 'month' else employee.appraisal_repeat_number * 12
            employee.write({'appraisal_date': fields.Date.to_string(current_date + relativedelta(months=months))})
            vals = {'employee_id': employee.id,
                    'date_close': current_date,
                    'manager_appraisal': employee.appraisal_by_manager,
                    'manager_ids': [(4, manager.id) for manager in employee.appraisal_manager_ids] or [(4, employee.parent_id.id)],
                    'manager_survey_id': employee.appraisal_manager_survey_id.id,
                    'colleagues_appraisal': employee.appraisal_by_colleagues,
                    'colleagues_ids': [(4, colleagues.id) for colleagues in employee.appraisal_colleagues_ids],
                    'colleagues_survey_id': employee.appraisal_colleagues_survey_id.id,
                    'employee_appraisal': employee.appraisal_self,
                    'employee_survey_id': employee.appraisal_self_survey_id.id,
                    'collaborators_appraisal': employee.appraisal_by_collaborators,
                    'collaborators_ids': [(4, subordinates.id) for subordinates in employee.appraisal_by_collaborators_ids],
                    'collaborators_survey_id': employee.appraisal_by_collaborators_survey_id.id}
            self.env['hr.appraisal'].create(vals)
        return True
